#pragma once

#include "esphome/components/binary_sensor/binary_sensor.h"
#include "esphome/components/select/select.h"
#include "esphome/components/switch/switch.h"
#include "esphome/components/uart/uart.h"
#include "esphome/core/component.h"
#include "esphome/core/log.h"

namespace esphome {
namespace ventilation_panel_bridge {

class VentilationPanelBridgeComponent;

class VentilationPanelBridgeModeSelect : public select::Select {
 public:
  void set_parent(VentilationPanelBridgeComponent *parent) { parent_ = parent; }

 protected:
  void control(size_t index) override;

  VentilationPanelBridgeComponent *parent_{nullptr};
};

class VentilationPanelBridgeBypassSwitch : public switch_::Switch {
 public:
  void set_parent(VentilationPanelBridgeComponent *parent) { parent_ = parent; }

 protected:
  void write_state(bool state) override;

  VentilationPanelBridgeComponent *parent_{nullptr};
};

class VentilationPanelBridgeComponent : public Component {
 public:
  void set_panel_uart(uart::UARTComponent *uart) { panel_uart_ = uart; }
  void set_controller_uart(uart::UARTComponent *uart) { controller_uart_ = uart; }
  void set_panel_connected(bool connected) { panel_connected_ = connected; }
  void set_mode_select(VentilationPanelBridgeModeSelect *select) { mode_select_ = select; }
  void set_bypass_switch(VentilationPanelBridgeBypassSwitch *switch_) { bypass_switch_ = switch_; }
  void set_filter_due_binary_sensor(binary_sensor::BinarySensor *sensor) { filter_due_binary_sensor_ = sensor; }
  void set_alarm_binary_sensor(binary_sensor::BinarySensor *sensor) { alarm_binary_sensor_ = sensor; }

  void setup() override {
    ESP_LOGCONFIG(TAG, "Ventilation panel bridge ready");
    this->publish_effective_command_(this->last_effective_command_);
  }

  void dump_config() override {
    ESP_LOGCONFIG(TAG, "Ventilation panel bridge");
    LOG_SELECT("  ", "Mode", this->mode_select_);
    LOG_SWITCH("  ", "Bypass", this->bypass_switch_);
    LOG_BINARY_SENSOR("  ", "Filter due", this->filter_due_binary_sensor_);
    LOG_BINARY_SENSOR("  ", "Alarm", this->alarm_binary_sensor_);
    ESP_LOGCONFIG(TAG, "  Panel connected: %s", YESNO(this->panel_connected_));
    if (this->panel_uart_ == nullptr)
      ESP_LOGCONFIG(TAG, "  Panel UART: not configured");
    if (this->controller_uart_ == nullptr)
      ESP_LOGCONFIG(TAG, "  Controller UART: not configured");
  }

  void loop() override {
    this->pump_panel_commands_();
    this->pump_controller_status_();
    this->pump_command_heartbeat_();
  }

  void set_mode_override(uint8_t mode) {
    this->mode_override_ = mode & MODE_MASK;
    this->mode_override_active_ = true;
    this->publish_pending_command_();
  }

  void set_bypass_override(bool bypass) {
    this->bypass_override_ = bypass;
    this->bypass_override_active_ = true;
    this->publish_pending_command_();
  }

 protected:
  static constexpr const char *TAG = "ventilation_panel_bridge";
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
  VentilationPanelBridgeModeSelect *mode_select_{nullptr};
  VentilationPanelBridgeBypassSwitch *bypass_switch_{nullptr};
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

  void pump_panel_commands_() {
    if (!this->panel_connected_ || this->panel_uart_ == nullptr || this->controller_uart_ == nullptr)
      return;

    uint8_t panel_command;
    uint8_t count = 0;
    while (count++ < MAX_BYTES_PER_LOOP && this->panel_uart_->available() &&
           this->panel_uart_->read_byte(&panel_command))
      this->handle_panel_command_(panel_command);
  }

  void handle_panel_command_(uint8_t panel_command) {
    if (this->have_panel_command_) {
      if ((panel_command & MODE_MASK) != (this->last_panel_command_ & MODE_MASK)) {
        this->mode_override_active_ = false;
        ESP_LOGD(TAG, "Panel mode changed to %u; releasing ESPHome mode override", panel_command & MODE_MASK);
      }
      if ((panel_command & BYPASS_MASK) != (this->last_panel_command_ & BYPASS_MASK)) {
        this->bypass_override_active_ = false;
        ESP_LOGD(TAG, "Panel bypass changed to %s; releasing ESPHome bypass override",
                 (panel_command & BYPASS_MASK) ? "open" : "closed");
      }
    }

    uint8_t effective_command = this->effective_command_(panel_command);
    this->have_panel_command_ = true;
    this->last_panel_command_ = panel_command;
    this->publish_effective_command_(effective_command);
  }

  uint8_t effective_command_(uint8_t panel_command) const {
    uint8_t effective_command = panel_command;
    if (this->mode_override_active_)
      effective_command = (effective_command & ~MODE_MASK) | this->mode_override_;
    if (this->bypass_override_active_) {
      if (this->bypass_override_)
        effective_command |= BYPASS_MASK;
      else
        effective_command &= ~BYPASS_MASK;
    }
    return effective_command;
  }

  void publish_pending_command_() {
    uint8_t base_command = this->have_panel_command_ ? this->last_panel_command_ : this->last_effective_command_;
    uint8_t effective_command = this->effective_command_(base_command);
    this->last_effective_command_ = effective_command;
    this->publish_effective_command_(effective_command);
  }

  void pump_controller_status_() {
    if (this->controller_uart_ == nullptr)
      return;

    uint8_t status;
    uint8_t count = 0;
    while (count++ < MAX_BYTES_PER_LOOP && this->controller_uart_->available() &&
           this->controller_uart_->read_byte(&status)) {
      if (this->panel_connected_ && this->panel_uart_ != nullptr)
        this->panel_uart_->write_byte(status);
      this->publish_controller_status_(status);
    }
  }

  void pump_command_heartbeat_() {
    if (this->controller_uart_ == nullptr)
      return;
    if (this->last_command_tx_ != 0 && !this->time_reached_(this->last_command_tx_ + COMMAND_HEARTBEAT_MS))
      return;

    uint8_t base_command = this->have_panel_command_ ? this->last_panel_command_ : this->last_effective_command_;
    this->transmit_effective_command_(this->effective_command_(base_command));
  }

  void transmit_effective_command_(uint8_t command) {
    if (this->controller_uart_ == nullptr)
      return;
    this->controller_uart_->write_byte(command);
    this->last_effective_command_ = command;
    this->last_command_tx_ = millis();
  }

  bool time_reached_(uint32_t deadline) const { return static_cast<int32_t>(millis() - deadline) >= 0; }

  void publish_effective_command_(uint8_t command) {
    bool first = !this->have_published_command_;
    if (this->mode_select_ != nullptr &&
        (first || (command & MODE_MASK) != (this->last_published_command_ & MODE_MASK)))
      this->mode_select_->publish_state(command & MODE_MASK);
    if (this->bypass_switch_ != nullptr &&
        (first || (command & BYPASS_MASK) != (this->last_published_command_ & BYPASS_MASK)))
      this->bypass_switch_->publish_state((command & BYPASS_MASK) != 0);
    this->have_published_command_ = true;
    this->last_published_command_ = command;
  }

  void publish_controller_status_(uint8_t status) {
    if (this->have_controller_status_ && this->last_controller_status_ == status)
      return;
    this->have_controller_status_ = true;
    this->last_controller_status_ = status;

    if (this->filter_due_binary_sensor_ != nullptr)
      this->filter_due_binary_sensor_->publish_state((status & STATUS_FILTER_DUE_MASK) != 0);
    if (this->alarm_binary_sensor_ != nullptr)
      this->alarm_binary_sensor_->publish_state((status & STATUS_ALARM_MASK) != 0);
  }
};

inline void VentilationPanelBridgeModeSelect::control(size_t index) {
  if (this->parent_ == nullptr)
    return;
  uint8_t mode = static_cast<uint8_t>(index);
  if (mode > 3)
    mode = 3;
  this->parent_->set_mode_override(mode);
}

inline void VentilationPanelBridgeBypassSwitch::write_state(bool state) {
  if (this->parent_ == nullptr)
    return;
  this->parent_->set_bypass_override(state);
}

}  // namespace ventilation_panel_bridge
}  // namespace esphome
