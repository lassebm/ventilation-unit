import esphome.codegen as cg
from esphome.components import binary_sensor, fan, switch, uart
from esphome.components.fan import validate_preset_modes
import esphome.config_validation as cv
from esphome.const import CONF_ID, CONF_PRESET_MODES, DEVICE_CLASS_PROBLEM, ICON_FAN

DEPENDENCIES = ["uart"]
AUTO_LOAD = ["binary_sensor", "fan", "switch"]

CONF_PANEL_UART_ID = "panel_uart_id"
CONF_CONTROLLER_UART_ID = "controller_uart_id"
CONF_PANEL_CONNECTED = "panel_connected"
CONF_MODE = "mode"
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
VentilationPanelBridgeBypassSwitch = ventilation_panel_bridge_ns.class_(
    "VentilationPanelBridgeBypassSwitch", switch.Switch
)


CONFIG_SCHEMA = cv.Schema(
    {
        cv.GenerateID(): cv.declare_id(VentilationPanelBridgeComponent),
        cv.Optional(CONF_PANEL_UART_ID): cv.use_id(uart.UARTComponent),
        cv.Required(CONF_CONTROLLER_UART_ID): cv.use_id(uart.UARTComponent),
        cv.Optional(CONF_PANEL_CONNECTED, default=True): cv.boolean,
        cv.Optional(CONF_MODE): fan.fan_schema(
            VentilationPanelBridgeModeFan,
            icon=ICON_FAN,
        ).extend(
            {
                # Named presets alias the three running speeds in order.
                cv.Optional(
                    CONF_PRESET_MODES, default=["Speed 1", "Speed 2", "Speed 3"]
                ): validate_preset_modes,
            }
        ),
        cv.Optional(CONF_BYPASS): switch.switch_schema(
            VentilationPanelBridgeBypassSwitch,
        ),
        cv.Optional(CONF_FILTER_DUE): binary_sensor.binary_sensor_schema(
            device_class=DEVICE_CLASS_PROBLEM,
        ),
        cv.Optional(CONF_ALARM): binary_sensor.binary_sensor_schema(
            device_class=DEVICE_CLASS_PROBLEM,
        ),
    }
).extend(cv.COMPONENT_SCHEMA)


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
            cg.add(mode_fan.set_preset_modes(preset_modes))
        cg.add(var.set_mode_fan(mode_fan))

    if bypass_config := config.get(CONF_BYPASS):
        sw = await switch.new_switch(bypass_config)
        cg.add(sw.set_parent(var))
        cg.add(var.set_bypass_switch(sw))

    if filter_due_config := config.get(CONF_FILTER_DUE):
        sens = await binary_sensor.new_binary_sensor(filter_due_config)
        cg.add(var.set_filter_due_binary_sensor(sens))

    if alarm_config := config.get(CONF_ALARM):
        sens = await binary_sensor.new_binary_sensor(alarm_config)
        cg.add(var.set_alarm_binary_sensor(sens))
