import esphome.codegen as cg
from esphome.components import binary_sensor, fan, switch, uart
from esphome.components.fan import validate_preset_modes
import esphome.config_validation as cv
from esphome.const import (
    CONF_ID,
    CONF_MODE,
    CONF_PRESET_MODES,
    DEVICE_CLASS_PROBLEM,
    ICON_FAN,
)

DOMAIN = "ventilation_panel_bridge"
DEPENDENCIES = ["uart"]
AUTO_LOAD = ["binary_sensor", "fan", "switch"]

CONF_PANEL_UART_ID = "panel_uart_id"
CONF_CONTROLLER_UART_ID = "controller_uart_id"
CONF_PANEL_CONNECTED = "panel_connected"
CONF_BYPASS = "bypass"
CONF_FILTER_DUE = "filter_due"
CONF_ALARM = "alarm"

ventilation_panel_bridge_ns = cg.esphome_ns.namespace("ventilation_panel_bridge")
VentilationPanelBridgeComponent = ventilation_panel_bridge_ns.class_(
    "VentilationPanelBridgeComponent", cg.Component
)
VentilationPanelBridgeModeFan = ventilation_panel_bridge_ns.class_(
    "VentilationPanelBridgeModeFan", fan.Fan, cg.Component
)


CONFIG_SCHEMA = cv.Schema(
    {
        cv.GenerateID(): cv.declare_id(VentilationPanelBridgeComponent),
        cv.Optional(CONF_PANEL_UART_ID): cv.use_id(uart.UARTComponent),
        cv.Required(CONF_CONTROLLER_UART_ID): cv.use_id(uart.UARTComponent),
        cv.Optional(CONF_PANEL_CONNECTED, default=True): cv.boolean,
        # Neither control restores by default: after a reboot the panel (or, without one, the
        # startup command: speed 1, bypass closed) decides. Set restore_mode to opt in.
        cv.Optional(CONF_MODE): fan.fan_schema(
            VentilationPanelBridgeModeFan,
            icon=ICON_FAN,
            default_restore_mode="NO_RESTORE",
        ).extend(
            {
                # Named presets alias the three running speeds in order.
                cv.Optional(
                    CONF_PRESET_MODES, default=["Speed 1", "Speed 2", "Speed 3"]
                ): validate_preset_modes,
            }
        ),
        cv.Optional(CONF_BYPASS): switch.switch_schema(
            switch.ApplySwitch, default_restore_mode="DISABLED"
        ),
        cv.Optional(CONF_FILTER_DUE): binary_sensor.binary_sensor_schema(
            device_class=DEVICE_CLASS_PROBLEM,
        ),
        cv.Optional(CONF_ALARM): binary_sensor.binary_sensor_schema(
            device_class=DEVICE_CLASS_PROBLEM,
        ),
    }
).extend(cv.COMPONENT_SCHEMA)


# Both panel-link UARTs are fixed at 600 8N1 — reject a mismatched uart at config time. The panel
# UART is optional (no physical panel), so its check only applies when it's configured.
_PANEL_LINK = {"baud_rate": 600, "data_bits": 8, "parity": "NONE", "stop_bits": 1}
_validate_controller_uart = uart.final_validate_device_schema(
    DOMAIN,
    uart_bus=CONF_CONTROLLER_UART_ID,
    require_tx=True,
    require_rx=True,
    **_PANEL_LINK,
)
_validate_panel_uart = uart.final_validate_device_schema(
    DOMAIN,
    uart_bus=CONF_PANEL_UART_ID,
    require_tx=True,
    require_rx=True,
    **_PANEL_LINK,
)


def _final_validate(config):
    _validate_controller_uart(config)
    if CONF_PANEL_UART_ID in config:
        _validate_panel_uart(config)
    return config


FINAL_VALIDATE_SCHEMA = _final_validate


async def to_code(config):
    var = cg.new_Pvariable(config[CONF_ID])
    await cg.register_component(var, config)

    if CONF_PANEL_UART_ID in config:
        panel_uart = await cg.get_variable(config[CONF_PANEL_UART_ID])
        cg.add(var.set_panel_uart(panel_uart))
    controller_uart = await cg.get_variable(config[CONF_CONTROLLER_UART_ID])
    cg.add(var.set_controller_uart(controller_uart))
    cg.add(var.set_panel_connected(config[CONF_PANEL_CONNECTED]))

    if mode_config := config.get(CONF_MODE):
        mode_fan = await fan.new_fan(mode_config)
        await cg.register_component(mode_fan, mode_config)
        cg.add(mode_fan.set_parent(var))
        if preset_modes := mode_config.get(CONF_PRESET_MODES):
            fan.set_preset_modes(mode_fan, preset_modes)
        cg.add(var.set_mode_fan(mode_fan))

    # The bridge publishes the bypass state once it's part of the effective command.
    switches = switch.sub_switches(config, parent=var)
    await switches(
        CONF_BYPASS, var.set_bypass_switch, apply="set_bypass_override(state)"
    )

    binary_sensors = binary_sensor.sub_binary_sensors(config)
    await binary_sensors(CONF_FILTER_DUE, var.set_filter_due_binary_sensor)
    await binary_sensors(CONF_ALARM, var.set_alarm_binary_sensor)
