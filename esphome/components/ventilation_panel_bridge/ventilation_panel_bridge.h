#pragma once

#include "esphome/components/binary_sensor/binary_sensor.h"
#include "esphome/components/fan/fan.h"
#include "esphome/components/switch/switch.h"
#include "esphome/components/uart/uart.h"
#include "esphome/core/component.h"

namespace esphome {
namespace ventilation_panel_bridge {

class VentilationPanelBridgeComponent;

class VentilationPanelBridgeModeFan final : public fan::Fan, public Component {
 public:
  void set_parent(VentilationPanelBridgeComponent *parent) { this->parent_ = parent; }

  fan::FanTraits get_traits() override {
    this->wire_preset_modes_(this->traits_);
    return this->traits_;
  }

  void dump_config() override;

  // The mode to restore at boot per the fan's restore_mode (0 = standby, 1-3 = speed), or nothing
  // when it doesn't restore (the default, NO_RESTORE).
  optional<uint8_t> restored_mode();

  // Reflect the actual panel mode (0 = Off/Standby, 1-3 = speed) into the fan entity.
  void publish_mode(uint8_t mode);

 protected:
  void control(const fan::FanCall &call) override;

  // Off (Standby) plus three ordered speeds, matching the controller's 2-bit mode field.
  fan::FanTraits traits_{false, true, false, 3};
  VentilationPanelBridgeComponent *parent_{nullptr};
};

class VentilationPanelBridgeComponent final : public Component {
 public:
  void set_panel_uart(uart::UARTComponent *uart) { this->panel_uart_ = uart; }
  void set_controller_uart(uart::UARTComponent *uart) { this->controller_uart_ = uart; }
  void set_panel_connected(bool connected) { this->panel_connected_ = connected; }
  void set_mode_fan(VentilationPanelBridgeModeFan *fan) { this->mode_fan_ = fan; }
  void set_bypass_switch(switch_::Switch *switch_) { this->bypass_switch_ = switch_; }
  void set_filter_due_binary_sensor(binary_sensor::BinarySensor *sensor) { this->filter_due_binary_sensor_ = sensor; }
  void set_alarm_binary_sensor(binary_sensor::BinarySensor *sensor) { this->alarm_binary_sensor_ = sensor; }

  void setup() override;
  void dump_config() override;
  void loop() override;
  void set_mode_override(uint8_t mode);
  void set_bypass_override(bool bypass);

 protected:
  static constexpr uint8_t MODE_MASK = 0x03;
  static constexpr uint8_t BYPASS_MASK = 0x08;
  static constexpr uint8_t STATUS_FILTER_DUE_MASK = 0x01;
  static constexpr uint8_t STATUS_ALARM_MASK = 0x02;
  static constexpr uint8_t MAX_BYTES_PER_LOOP = 8;
  // Controller firmware debounces panel command changes over roughly 10 repeated bytes.
  static constexpr uint32_t COMMAND_HEARTBEAT_MS = 100;

  uart::UARTComponent *panel_uart_{nullptr};
  uart::UARTComponent *controller_uart_{nullptr};
  bool panel_connected_{true};
  VentilationPanelBridgeModeFan *mode_fan_{nullptr};
  switch_::Switch *bypass_switch_{nullptr};
  binary_sensor::BinarySensor *filter_due_binary_sensor_{nullptr};
  binary_sensor::BinarySensor *alarm_binary_sensor_{nullptr};

  bool have_panel_command_{false};
  uint8_t last_panel_command_{0};
  // No-panel startup command: mode 1, bypass closed.
  uint8_t last_effective_command_{0x01};
  bool mode_override_active_{false};
  uint8_t mode_override_{0};
  bool bypass_override_active_{false};
  bool bypass_override_{false};
  bool have_controller_status_{false};
  uint8_t last_controller_status_{0};
  bool have_published_command_{false};
  uint8_t last_published_command_{0};
  uint32_t last_command_tx_{0};

  void pump_panel_commands_();
  void handle_panel_command_(uint8_t panel_command);
  uint8_t effective_command_(uint8_t panel_command) const;
  void publish_pending_command_();
  void pump_controller_status_();
  void pump_command_heartbeat_();
  void transmit_effective_command_(uint8_t command);

  bool time_reached_(uint32_t deadline) const { return static_cast<int32_t>(millis() - deadline) >= 0; }

  void publish_effective_command_(uint8_t command);
  void publish_controller_status_(uint8_t status);
};

}  // namespace ventilation_panel_bridge
}  // namespace esphome
