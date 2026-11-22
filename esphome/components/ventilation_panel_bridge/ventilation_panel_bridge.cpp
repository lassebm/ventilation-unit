#include "ventilation_panel_bridge.h"

#include "esphome/core/log.h"

namespace esphome {
namespace ventilation_panel_bridge {

ESPHOME_LOG_TAG(TAG, "ventilation_panel_bridge");

void VentilationPanelBridgeComponent::setup() {
  ESP_LOGCONFIG(TAG, "Ventilation panel bridge ready");
  this->publish_effective_command_(this->last_effective_command_);
  // Opt-in restore (restore_mode on the mode fan / bypass switch): re-apply the last mode/bypass as
  // overrides, which hold until the panel changes them, like any other override.
  if (this->mode_fan_ != nullptr) {
    if (auto mode = this->mode_fan_->restored_mode())
      this->set_mode_override(*mode);
  }
  if (this->bypass_switch_ != nullptr)
    this->bypass_switch_->restore();  // no-op when restore_mode is DISABLED (the default)
}

void VentilationPanelBridgeComponent::dump_config() {
  ESP_LOGCONFIG(TAG, "Ventilation panel bridge");
  LOG_SWITCH("  ", "Bypass", this->bypass_switch_);
  LOG_BINARY_SENSOR("  ", "Filter due", this->filter_due_binary_sensor_);
  LOG_BINARY_SENSOR("  ", "Alarm", this->alarm_binary_sensor_);
  ESP_LOGCONFIG(TAG, "  Panel connected: %s", YESNO(this->panel_connected_));
  if (this->panel_uart_ == nullptr) {
    ESP_LOGCONFIG(TAG, "  Panel UART: not configured");
  }
  if (this->controller_uart_ == nullptr) {
    ESP_LOGCONFIG(TAG, "  Controller UART: not configured");
  }
}

void VentilationPanelBridgeComponent::loop() {
  this->pump_panel_commands_();
  this->pump_controller_status_();
  this->pump_command_heartbeat_();
}

void VentilationPanelBridgeComponent::set_mode_override(uint8_t mode) {
  this->mode_override_ = mode & MODE_MASK;
  this->mode_override_active_ = true;
  this->publish_pending_command_();
}

void VentilationPanelBridgeComponent::set_bypass_override(bool bypass) {
  this->bypass_override_ = bypass;
  this->bypass_override_active_ = true;
  this->publish_pending_command_();
}

void VentilationPanelBridgeComponent::pump_panel_commands_() {
  if (!this->panel_connected_ || this->panel_uart_ == nullptr || this->controller_uart_ == nullptr)
    return;

  uint8_t panel_command;
  uint8_t count = 0;
  while (count++ < MAX_BYTES_PER_LOOP && this->panel_uart_->available() && this->panel_uart_->read_byte(&panel_command))
    this->handle_panel_command_(panel_command);
}

void VentilationPanelBridgeComponent::handle_panel_command_(uint8_t panel_command) {
  if (this->have_panel_command_) {
    if ((panel_command & MODE_MASK) != (this->last_panel_command_ & MODE_MASK)) {
      this->mode_override_active_ = false;
      ESP_LOGD(TAG, "Panel mode changed to %u; releasing ESPHome mode override", panel_command & MODE_MASK);
    }
    if ((panel_command & BYPASS_MASK) != (this->last_panel_command_ & BYPASS_MASK)) {
      this->bypass_override_active_ = false;
      ESP_LOGD(TAG, "Panel bypass changed to %s; releasing ESPHome bypass override",
               (panel_command & BYPASS_MASK) ? LOG_STR_LITERAL("open") : LOG_STR_LITERAL("closed"));
    }
  }

  uint8_t effective_command = this->effective_command_(panel_command);
  this->have_panel_command_ = true;
  this->last_panel_command_ = panel_command;
  this->publish_effective_command_(effective_command);
}

uint8_t VentilationPanelBridgeComponent::effective_command_(uint8_t panel_command) const {
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

void VentilationPanelBridgeComponent::publish_pending_command_() {
  uint8_t base_command = this->have_panel_command_ ? this->last_panel_command_ : this->last_effective_command_;
  uint8_t effective_command = this->effective_command_(base_command);
  this->last_effective_command_ = effective_command;
  this->publish_effective_command_(effective_command);
}

void VentilationPanelBridgeComponent::pump_controller_status_() {
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

void VentilationPanelBridgeComponent::pump_command_heartbeat_() {
  if (this->controller_uart_ == nullptr)
    return;
  if (this->last_command_tx_ != 0 && !this->time_reached_(this->last_command_tx_ + COMMAND_HEARTBEAT_MS))
    return;

  uint8_t base_command = this->have_panel_command_ ? this->last_panel_command_ : this->last_effective_command_;
  this->transmit_effective_command_(this->effective_command_(base_command));
}

void VentilationPanelBridgeComponent::transmit_effective_command_(uint8_t command) {
  if (this->controller_uart_ == nullptr)
    return;
  this->controller_uart_->write_byte(command);
  this->last_effective_command_ = command;
  this->last_command_tx_ = millis();
}

void VentilationPanelBridgeComponent::publish_effective_command_(uint8_t command) {
  bool first = !this->have_published_command_;
  if (this->mode_fan_ != nullptr && (first || (command & MODE_MASK) != (this->last_published_command_ & MODE_MASK)))
    this->mode_fan_->publish_mode(command & MODE_MASK);
  if (this->bypass_switch_ != nullptr &&
      (first || (command & BYPASS_MASK) != (this->last_published_command_ & BYPASS_MASK)))
    this->bypass_switch_->publish_state((command & BYPASS_MASK) != 0);
  this->have_published_command_ = true;
  this->last_published_command_ = command;
}

void VentilationPanelBridgeComponent::publish_controller_status_(uint8_t status) {
  if (this->have_controller_status_ && this->last_controller_status_ == status)
    return;
  this->have_controller_status_ = true;
  this->last_controller_status_ = status;

  if (this->filter_due_binary_sensor_ != nullptr)
    this->filter_due_binary_sensor_->publish_state((status & STATUS_FILTER_DUE_MASK) != 0);
  if (this->alarm_binary_sensor_ != nullptr)
    this->alarm_binary_sensor_->publish_state((status & STATUS_ALARM_MASK) != 0);
}

}  // namespace ventilation_panel_bridge
}  // namespace esphome
