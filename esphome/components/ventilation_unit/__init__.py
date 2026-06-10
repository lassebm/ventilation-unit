import esphome.codegen as cg
import esphome.config_validation as cv
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

DEPENDENCIES = ["usb_uart"]
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
VentilationUnitNumber = ventilation_unit_ns.class_("VentilationUnitNumber", number.Number)
VentilationUnitSwitch = ventilation_unit_ns.class_("VentilationUnitSwitch", switch.Switch)
VentilationUnitEditModeSwitch = ventilation_unit_ns.class_(
    "VentilationUnitEditModeSwitch", switch.Switch
)
VentilationUnitButton = ventilation_unit_ns.class_("VentilationUnitButton", button.Button)


def setpoint_schema():
    return number.number_schema(
        VentilationUnitNumber,
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
    return cv.Schema(
        {cv.Optional(key): setpoint_schema() for key in SPEED_SETPOINTS}
    )


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
            ),
            cv.Optional(CONF_HUMIDITY_VOLTAGE): sensor.sensor_schema(
                unit_of_measurement=UNIT_VOLT,
                accuracy_decimals=2,
                device_class=DEVICE_CLASS_VOLTAGE,
                state_class=STATE_CLASS_MEASUREMENT,
                entity_category=ENTITY_CATEGORY_DIAGNOSTIC,
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
                VentilationUnitEditModeSwitch,
                default_restore_mode="ALWAYS_OFF",
                entity_category=ENTITY_CATEGORY_CONFIG,
            ),
            cv.Optional(CONF_BYPASS_HARDWARE_PRESENT): switch.switch_schema(
                VentilationUnitSwitch,
                default_restore_mode="DISABLED",
                entity_category=ENTITY_CATEGORY_CONFIG,
            ),
            cv.Optional(CONF_BYPASS_POLARITY_INVERT): switch.switch_schema(
                VentilationUnitSwitch,
                default_restore_mode="DISABLED",
                entity_category=ENTITY_CATEGORY_CONFIG,
            ),
            cv.Optional(CONF_FILTER_RUNTIME): sensor.sensor_schema(
                unit_of_measurement=UNIT_HOUR,
                accuracy_decimals=1,
                icon=ICON_TIMER,
                state_class=STATE_CLASS_MEASUREMENT,
            ),
            cv.Optional(CONF_FILTER_REPLACEMENT_INTERVAL): number.number_schema(
                VentilationUnitNumber,
                unit_of_measurement=UNIT_HOUR,
                icon=ICON_TIMER,
                entity_category=ENTITY_CATEGORY_CONFIG,
            ),
            cv.Optional(CONF_FILTER_REPLACEMENT_RESET): button.button_schema(
                VentilationUnitButton,
                icon=ICON_RESTART,
                entity_category=ENTITY_CATEGORY_CONFIG,
            ),
            cv.Optional(CONF_FREEZE_PROTECTION_THRESHOLD): number.number_schema(
                VentilationUnitNumber,
                unit_of_measurement=UNIT_CELSIUS,
                device_class=DEVICE_CLASS_TEMPERATURE,
                entity_category=ENTITY_CATEGORY_CONFIG,
            ),
            cv.Optional(CONF_HUMIDITY_BOOST_THRESHOLD): number.number_schema(
                VentilationUnitNumber,
                unit_of_measurement=UNIT_PERCENT,
                device_class=DEVICE_CLASS_HUMIDITY,
                entity_category=ENTITY_CATEGORY_CONFIG,
            ),
            cv.Optional(CONF_INFLOW_SPEED_SETPOINTS): speed_setpoints_schema(),
            cv.Optional(CONF_OUTFLOW_SPEED_SETPOINTS): speed_setpoints_schema(),
            cv.Optional(CONF_FIRMWARE_VERSION): text_sensor.text_sensor_schema(
                entity_category="diagnostic"
            ),
        }
    )
    .extend(cv.polling_component_schema("30s"))
    .extend(cv.Schema({cv.GenerateID(CONF_UART_ID): cv.use_id(usb_uart.USBUartChannel)}))
)


async def to_code(config):
    var = cg.new_Pvariable(config[CONF_ID])
    await cg.register_component(var, config)
    await uart.register_uart_device(var, config)

    if temperature_config := config.get(CONF_TEMPERATURE):
        sens = await sensor.new_sensor(temperature_config)
        cg.add(var.set_temperature_sensor(sens))
    if humidity_config := config.get(CONF_HUMIDITY):
        sens = await sensor.new_sensor(humidity_config)
        cg.add(var.set_humidity_sensor(sens))
    if humidity_voltage_config := config.get(CONF_HUMIDITY_VOLTAGE):
        sens = await sensor.new_sensor(humidity_voltage_config)
        cg.add(var.set_humidity_voltage_sensor(sens))
    if inflow_config := config.get(CONF_INFLOW_RPM):
        sens = await sensor.new_sensor(inflow_config)
        cg.add(var.set_inflow_rpm_sensor(sens))
    if outflow_config := config.get(CONF_OUTFLOW_RPM):
        sens = await sensor.new_sensor(outflow_config)
        cg.add(var.set_outflow_rpm_sensor(sens))
    if force_input_config := config.get(CONF_FORCE_INPUT):
        sens = await binary_sensor.new_binary_sensor(force_input_config)
        cg.add(var.set_force_input_binary_sensor(sens))
    if bypass_config := config.get(CONF_BYPASS_STATE):
        sens = await binary_sensor.new_binary_sensor(bypass_config)
        cg.add(var.set_bypass_binary_sensor(sens))
    if edit_mode_config := config.get(CONF_EDIT_MODE):
        sw = await switch.new_switch(edit_mode_config)
        cg.add(sw.set_parent(var))
        cg.add(var.set_edit_mode_switch(sw))
    if bypass_hardware_present_config := config.get(CONF_BYPASS_HARDWARE_PRESENT):
        sw = await switch.new_switch(bypass_hardware_present_config)
        cg.add(sw.set_parent(var))
        cg.add(sw.set_register(REG_BYPASS_HARDWARE_PRESENT))
        cg.add(var.set_bypass_hardware_present_switch(sw))
    if bypass_polarity_invert_config := config.get(CONF_BYPASS_POLARITY_INVERT):
        sw = await switch.new_switch(bypass_polarity_invert_config)
        cg.add(sw.set_parent(var))
        cg.add(sw.set_register(REG_BYPASS_POLARITY_INVERT))
        cg.add(var.set_bypass_polarity_invert_switch(sw))
    if filter_runtime_config := config.get(CONF_FILTER_RUNTIME):
        sens = await sensor.new_sensor(filter_runtime_config)
        cg.add(var.set_filter_runtime_sensor(sens))
    if filter_replacement_interval_config := config.get(
        CONF_FILTER_REPLACEMENT_INTERVAL
    ):
        num = await number.new_number(
            filter_replacement_interval_config,
            min_value=1,
            max_value=9999,
            step=1,
        )
        cg.add(num.set_parent(var))
        cg.add(num.set_register(REG_FILTER_REPLACEMENT_INTERVAL))
        cg.add(num.set_scale(6.0))
        cg.add(var.set_filter_replacement_interval_number(num))
    if filter_replacement_reset_config := config.get(CONF_FILTER_REPLACEMENT_RESET):
        btn = await button.new_button(filter_replacement_reset_config)
        cg.add(btn.set_parent(var))
        cg.add(btn.set_register(REG_FILTER_REPLACEMENT_RESET))
        cg.add(btn.set_value(1))
        cg.add(var.set_filter_replacement_reset_button(btn))
    if freeze_protection_threshold_config := config.get(
        CONF_FREEZE_PROTECTION_THRESHOLD
    ):
        num = await number.new_number(
            freeze_protection_threshold_config, min_value=1, max_value=31, step=1
        )
        cg.add(num.set_parent(var))
        cg.add(num.set_register(REG_FREEZE_PROTECTION_THRESHOLD))
        cg.add(num.set_scale(1.0))
        cg.add(var.set_freeze_protection_threshold_number(num))

    if humidity_boost_threshold_config := config.get(CONF_HUMIDITY_BOOST_THRESHOLD):
        num = await number.new_number(
            humidity_boost_threshold_config, min_value=30, max_value=80, step=1
        )
        cg.add(num.set_parent(var))
        cg.add(num.set_register(REG_HUMIDITY_BOOST_THRESHOLD))
        cg.add(num.set_scale(1.0))
        cg.add(var.set_humidity_boost_threshold_number(num))

    for key, setter, base_reg in (
        (
            CONF_INFLOW_SPEED_SETPOINTS,
            "set_inflow_speed_setpoint_number",
            REG_INFLOW_SPEED_SETPOINT_BASE,
        ),
        (
            CONF_OUTFLOW_SPEED_SETPOINTS,
            "set_outflow_speed_setpoint_number",
            REG_OUTFLOW_SPEED_SETPOINT_BASE,
        ),
    ):
        speed_setpoints_config = config.get(key)
        if speed_setpoints_config is None:
            continue
        for i, setpoint_key in enumerate(SPEED_SETPOINTS):
            if setpoint_key not in speed_setpoints_config:
                continue
            number_config = speed_setpoints_config[setpoint_key]
            num = await number.new_number(
                number_config, min_value=0, max_value=100, step=1
            )
            cg.add(num.set_parent(var))
            cg.add(num.set_register(base_reg + i))
            cg.add(num.set_scale(10.0))
            cg.add(getattr(var, setter)(i, num))

    if firmware_config := config.get(CONF_FIRMWARE_VERSION):
        sens = await text_sensor.new_text_sensor(firmware_config)
        cg.add(var.set_firmware_version_text_sensor(sens))
