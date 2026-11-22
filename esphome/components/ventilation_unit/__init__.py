import esphome.codegen as cg
from esphome.components import (
    binary_sensor,
    button,
    number,
    sensor,
    switch,
    text_sensor,
    uart,
    usb_uart,
)
import esphome.config_validation as cv
from esphome.const import (
    CONF_HUMIDITY,
    CONF_ID,
    CONF_TEMPERATURE,
    CONF_UART_ID,
    DEVICE_CLASS_HUMIDITY,
    DEVICE_CLASS_TEMPERATURE,
    DEVICE_CLASS_VOLTAGE,
    ENTITY_CATEGORY_CONFIG,
    ENTITY_CATEGORY_DIAGNOSTIC,
    ICON_AIR_FILTER,
    ICON_FAN,
    ICON_RESTART,
    ICON_TIMER,
    STATE_CLASS_MEASUREMENT,
    UNIT_CELSIUS,
    UNIT_HOUR,
    UNIT_PERCENT,
    UNIT_REVOLUTIONS_PER_MINUTE,
    UNIT_VOLT,
)
from esphome.core import CORE

# The controller link is a usb_uart channel (CP210X) on the ESP32. On the `host` platform any
# serial port works instead (a USB-serial adapter on a Linux box, or the test suite's pty), so the
# hard dependency is just `uart`; the uart_id validator below picks the right class.
DOMAIN = "ventilation_unit"
DEPENDENCIES = ["uart"]
AUTO_LOAD = ["binary_sensor", "button", "number", "sensor", "switch", "text_sensor"]

# CONF_TEMPERATURE and CONF_HUMIDITY are imported from esphome.const.
CONF_HUMIDITY_VOLTAGE = "humidity_voltage"
CONF_INFLOW_RPM = "inflow_rpm"
CONF_OUTFLOW_RPM = "outflow_rpm"
CONF_FORCE_INPUT = "force_input"
CONF_BYPASS_STATE = "bypass_state"
CONF_EDIT_MODE = "edit_mode"
CONF_BYPASS_HARDWARE_PRESENT = "bypass_hardware_present"
CONF_BYPASS_POLARITY_INVERT = "bypass_polarity_invert"
CONF_FILTER_RUNTIME = "filter_runtime"
CONF_FILTER_LIFE_REMAINING = "filter_life_remaining"
CONF_FILTER_REMAINING_HOURS = "filter_remaining_hours"
CONF_FILTER_REPLACEMENT_INTERVAL = "filter_replacement_interval"
CONF_FILTER_REPLACEMENT_RESET = "filter_replacement_reset"
CONF_FREEZE_PROTECTION_THRESHOLD = "freeze_protection_threshold"
CONF_HUMIDITY_BOOST_THRESHOLD = "humidity_boost_threshold"
CONF_INFLOW_SPEED_SETPOINTS = "inflow_speed_setpoints"
CONF_OUTFLOW_SPEED_SETPOINTS = "outflow_speed_setpoints"
CONF_FIRMWARE_VERSION = "firmware_version"

CONF_SPEED_STANDBY = "standby"
CONF_SPEED_1 = "speed_1"
CONF_SPEED_2 = "speed_2"
CONF_SPEED_3 = "speed_3"
CONF_SPEED_FORCE_INPUT = "force_input"
CONF_SPEED_HUMIDITY_BOOST = "humidity_boost"

REG_INFLOW_SPEED_SETPOINT_BASE = 0x10
REG_OUTFLOW_SPEED_SETPOINT_BASE = 0x20
REG_BYPASS_HARDWARE_PRESENT = 0x31
REG_BYPASS_POLARITY_INVERT = 0x32
REG_FILTER_REPLACEMENT_RESET = 0x54
REG_FILTER_REPLACEMENT_INTERVAL = 0x55
REG_FREEZE_PROTECTION_THRESHOLD = 0x70
REG_HUMIDITY_BOOST_THRESHOLD = 0x72

ventilation_unit_ns = cg.esphome_ns.namespace("ventilation_unit")
VentilationUnitComponent = ventilation_unit_ns.class_(
    "VentilationUnitComponent", cg.PollingComponent, uart.UARTDevice
)


def _uart_id(value):
    if CORE.is_host:
        return cv.use_id(uart.UARTComponent)(value)
    return cv.use_id(usb_uart.USBUartChannel)(value)


def setpoint_schema():
    return number.number_schema(
        number.ApplyNumber,
        unit_of_measurement=UNIT_PERCENT,
        icon=ICON_FAN,
        entity_category=ENTITY_CATEGORY_CONFIG,
    )


SPEED_SETPOINTS = (
    CONF_SPEED_STANDBY,
    CONF_SPEED_1,
    CONF_SPEED_2,
    CONF_SPEED_3,
    CONF_SPEED_FORCE_INPUT,
    CONF_SPEED_HUMIDITY_BOOST,
)


def speed_setpoints_schema():
    return cv.Schema({cv.Optional(key): setpoint_schema() for key in SPEED_SETPOINTS})


CONFIG_SCHEMA = (
    cv.Schema(
        {
            cv.GenerateID(): cv.declare_id(VentilationUnitComponent),
            cv.Optional(CONF_TEMPERATURE): sensor.sensor_schema(
                unit_of_measurement=UNIT_CELSIUS,
                accuracy_decimals=0,
                device_class=DEVICE_CLASS_TEMPERATURE,
                state_class=STATE_CLASS_MEASUREMENT,
            ),
            cv.Optional(CONF_HUMIDITY): sensor.sensor_schema(
                unit_of_measurement=UNIT_PERCENT,
                accuracy_decimals=1,
                device_class=DEVICE_CLASS_HUMIDITY,
                state_class=STATE_CLASS_MEASUREMENT,
                filters=[
                    {"throttle_average": cv.TimePeriod(seconds=60)},
                    {"round": 1},
                ],
            ),
            cv.Optional(CONF_HUMIDITY_VOLTAGE): sensor.sensor_schema(
                unit_of_measurement=UNIT_VOLT,
                accuracy_decimals=2,
                device_class=DEVICE_CLASS_VOLTAGE,
                state_class=STATE_CLASS_MEASUREMENT,
                entity_category=ENTITY_CATEGORY_DIAGNOSTIC,
                filters=[
                    {"throttle_average": cv.TimePeriod(seconds=60)},
                    {"round": 2},
                ],
            ),
            cv.Optional(CONF_INFLOW_RPM): sensor.sensor_schema(
                unit_of_measurement=UNIT_REVOLUTIONS_PER_MINUTE,
                accuracy_decimals=0,
                icon=ICON_FAN,
                state_class=STATE_CLASS_MEASUREMENT,
            ),
            cv.Optional(CONF_OUTFLOW_RPM): sensor.sensor_schema(
                unit_of_measurement=UNIT_REVOLUTIONS_PER_MINUTE,
                accuracy_decimals=0,
                icon=ICON_FAN,
                state_class=STATE_CLASS_MEASUREMENT,
            ),
            cv.Optional(CONF_FORCE_INPUT): binary_sensor.binary_sensor_schema(),
            cv.Optional(CONF_BYPASS_STATE): binary_sensor.binary_sensor_schema(),
            cv.Optional(CONF_EDIT_MODE): switch.switch_schema(
                switch.ApplySwitch,
                default_restore_mode="ALWAYS_OFF",
                entity_category=ENTITY_CATEGORY_CONFIG,
            ),
            cv.Optional(CONF_BYPASS_HARDWARE_PRESENT): switch.switch_schema(
                switch.ApplySwitch,
                default_restore_mode="DISABLED",
                entity_category=ENTITY_CATEGORY_CONFIG,
            ),
            cv.Optional(CONF_BYPASS_POLARITY_INVERT): switch.switch_schema(
                switch.ApplySwitch,
                default_restore_mode="DISABLED",
                entity_category=ENTITY_CATEGORY_CONFIG,
            ),
            cv.Optional(CONF_FILTER_RUNTIME): sensor.sensor_schema(
                unit_of_measurement=UNIT_HOUR,
                accuracy_decimals=1,
                icon=ICON_TIMER,
                state_class=STATE_CLASS_MEASUREMENT,
            ),
            cv.Optional(CONF_FILTER_LIFE_REMAINING): sensor.sensor_schema(
                unit_of_measurement=UNIT_PERCENT,
                accuracy_decimals=0,
                icon=ICON_AIR_FILTER,
                state_class=STATE_CLASS_MEASUREMENT,
            ),
            cv.Optional(CONF_FILTER_REMAINING_HOURS): sensor.sensor_schema(
                unit_of_measurement=UNIT_HOUR,
                accuracy_decimals=1,
                icon=ICON_TIMER,
                state_class=STATE_CLASS_MEASUREMENT,
            ),
            cv.Optional(CONF_FILTER_REPLACEMENT_INTERVAL): number.number_schema(
                number.ApplyNumber,
                unit_of_measurement=UNIT_HOUR,
                icon=ICON_TIMER,
                entity_category=ENTITY_CATEGORY_CONFIG,
            ),
            cv.Optional(CONF_FILTER_REPLACEMENT_RESET): button.button_schema(
                button.ApplyButton,
                icon=ICON_RESTART,
                entity_category=ENTITY_CATEGORY_CONFIG,
            ),
            cv.Optional(CONF_FREEZE_PROTECTION_THRESHOLD): number.number_schema(
                number.ApplyNumber,
                unit_of_measurement=UNIT_CELSIUS,
                device_class=DEVICE_CLASS_TEMPERATURE,
                entity_category=ENTITY_CATEGORY_CONFIG,
            ),
            cv.Optional(CONF_HUMIDITY_BOOST_THRESHOLD): number.number_schema(
                number.ApplyNumber,
                unit_of_measurement=UNIT_PERCENT,
                device_class=DEVICE_CLASS_HUMIDITY,
                entity_category=ENTITY_CATEGORY_CONFIG,
            ),
            cv.Optional(CONF_INFLOW_SPEED_SETPOINTS): speed_setpoints_schema(),
            cv.Optional(CONF_OUTFLOW_SPEED_SETPOINTS): speed_setpoints_schema(),
            cv.Optional(CONF_FIRMWARE_VERSION): text_sensor.text_sensor_schema(
                entity_category=ENTITY_CATEGORY_DIAGNOSTIC
            ),
        }
    )
    .extend(cv.polling_component_schema("30s"))
    .extend(cv.Schema({cv.GenerateID(CONF_UART_ID): _uart_id}))
)

# The controller's USB/PC link is fixed at 38400 8N1 — reject a mismatched channel at config time.
FINAL_VALIDATE_SCHEMA = uart.final_validate_device_schema(
    DOMAIN, baud_rate=38400, data_bits=8, parity="NONE", stop_bits=1
)


async def to_code(config):
    var = cg.new_Pvariable(config[CONF_ID])
    await cg.register_component(var, config)
    await uart.register_uart_device(var, config)

    # Read-only entities: the hub publishes them from its refresh cycle.
    sensors = sensor.sub_sensors(config)
    await sensors(CONF_TEMPERATURE, var.set_temperature_sensor)
    await sensors(CONF_HUMIDITY, var.set_humidity_sensor)
    await sensors(CONF_HUMIDITY_VOLTAGE, var.set_humidity_voltage_sensor)
    await sensors(CONF_INFLOW_RPM, var.set_inflow_rpm_sensor)
    await sensors(CONF_OUTFLOW_RPM, var.set_outflow_rpm_sensor)
    await sensors(CONF_FILTER_RUNTIME, var.set_filter_runtime_sensor)
    await sensors(CONF_FILTER_LIFE_REMAINING, var.set_filter_life_remaining_sensor)
    await sensors(CONF_FILTER_REMAINING_HOURS, var.set_filter_remaining_hours_sensor)
    binary_sensors = binary_sensor.sub_binary_sensors(config)
    await binary_sensors(CONF_FORCE_INPUT, var.set_force_input_binary_sensor)
    await binary_sensors(CONF_BYPASS_STATE, var.set_bypass_binary_sensor)
    text_sensors = text_sensor.sub_text_sensors(config)
    await text_sensors(CONF_FIRMWARE_VERSION, var.set_firmware_version_text_sensor)

    # Writable entities forward to the hub, which gates them on edit mode, writes the register,
    # commits it to flash, and publishes the confirmed value. So none of them publish on their own.
    switches = switch.sub_switches(config, parent=var)
    await switches(
        CONF_EDIT_MODE, var.set_edit_mode_switch, apply="set_edit_mode(state)"
    )
    for key, setter, reg in (
        (
            CONF_BYPASS_HARDWARE_PRESENT,
            var.set_bypass_hardware_present_switch,
            REG_BYPASS_HARDWARE_PRESENT,
        ),
        (
            CONF_BYPASS_POLARITY_INVERT,
            var.set_bypass_polarity_invert_switch,
            REG_BYPASS_POLARITY_INVERT,
        ),
    ):
        await switches(key, setter, apply=f"queue_write({reg}, state ? 1 : 0)")

    buttons = button.sub_buttons(config, parent=var)
    await buttons(
        CONF_FILTER_REPLACEMENT_RESET,
        var.set_filter_replacement_reset_button,
        apply=f"queue_write({REG_FILTER_REPLACEMENT_RESET}, 1)",
    )

    # Numbers are written in display units; the hub scales them to raw register units.
    numbers = number.sub_numbers(config, parent=var)
    for key, setter, reg, (lo, hi) in (
        (
            CONF_FILTER_REPLACEMENT_INTERVAL,
            var.set_filter_replacement_interval_number,
            REG_FILTER_REPLACEMENT_INTERVAL,
            (1, 9999),
        ),
        (
            CONF_FREEZE_PROTECTION_THRESHOLD,
            var.set_freeze_protection_threshold_number,
            REG_FREEZE_PROTECTION_THRESHOLD,
            (1, 31),
        ),
        (
            CONF_HUMIDITY_BOOST_THRESHOLD,
            var.set_humidity_boost_threshold_number,
            REG_HUMIDITY_BOOST_THRESHOLD,
            (30, 80),
        ),
    ):
        await numbers(
            key,
            setter,
            min_value=lo,
            max_value=hi,
            step=1,
            apply=f"write_number({reg}, value)",
        )

    for key, setter, base_reg in (
        (
            CONF_INFLOW_SPEED_SETPOINTS,
            var.set_inflow_speed_setpoint_number,
            REG_INFLOW_SPEED_SETPOINT_BASE,
        ),
        (
            CONF_OUTFLOW_SPEED_SETPOINTS,
            var.set_outflow_speed_setpoint_number,
            REG_OUTFLOW_SPEED_SETPOINT_BASE,
        ),
    ):
        if (speed_setpoints_config := config.get(key)) is None:
            continue
        setpoints = number.sub_numbers(speed_setpoints_config, parent=var)
        for i, setpoint_key in enumerate(SPEED_SETPOINTS):
            await setpoints(
                setpoint_key,
                lambda num, setter=setter, i=i: setter(i, num),
                min_value=0,
                max_value=100,
                step=1,
                apply=f"write_number({base_reg + i}, value)",
            )
