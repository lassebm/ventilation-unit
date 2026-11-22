#include "ventilation_unit.h"

#include "esphome/core/log.h"

#include <cstdio>

namespace esphome {
namespace ventilation_unit {

ESPHOME_LOG_TAG(TAG, "ventilation_unit");

void VentilationUnitComponent::setup() {
  ESP_LOGCONFIG(TAG, "Ventilation unit ready");
  if (this->edit_mode_switch_ != nullptr)
    this->edit_mode_switch_->publish_state(this->edit_mode_);
}

void VentilationUnitComponent::dump_config() {
  ESP_LOGCONFIG(TAG, "Ventilation unit");
  LOG_UPDATE_INTERVAL(this);
  LOG_SENSOR("  ", "Temperature", this->temperature_sensor_);
  LOG_SENSOR("  ", "Humidity", this->humidity_sensor_);
  LOG_SENSOR("  ", "Humidity voltage", this->humidity_voltage_sensor_);
  LOG_SENSOR("  ", "Inflow RPM", this->inflow_rpm_sensor_);
  LOG_SENSOR("  ", "Outflow RPM", this->outflow_rpm_sensor_);
  LOG_BINARY_SENSOR("  ", "Force input", this->force_input_binary_sensor_);
  LOG_BINARY_SENSOR("  ", "Bypass", this->bypass_binary_sensor_);
  LOG_SWITCH("  ", "Edit mode", this->edit_mode_switch_);
  LOG_SWITCH("  ", "Bypass hardware present", this->bypass_hardware_present_switch_);
  LOG_SWITCH("  ", "Bypass polarity invert", this->bypass_polarity_invert_switch_);
  LOG_SENSOR("  ", "Filter runtime", this->filter_runtime_sensor_);
  LOG_SENSOR("  ", "Filter life remaining", this->filter_life_remaining_sensor_);
  LOG_SENSOR("  ", "Filter remaining hours", this->filter_remaining_hours_sensor_);
  LOG_NUMBER("  ", "Filter replacement interval", this->filter_replacement_interval_number_);
  LOG_BUTTON("  ", "Filter replacement reset", this->filter_replacement_reset_button_);
  LOG_NUMBER("  ", "Freeze protection threshold", this->freeze_protection_threshold_number_);
  LOG_NUMBER("  ", "Humidity boost threshold", this->humidity_boost_threshold_number_);
  LOG_TEXT_SENSOR("  ", "Firmware version", this->firmware_version_text_sensor_);
}

void VentilationUnitComponent::update() {
  if (this->state_ != State::IDLE)
    return;
  if (!this->parent_ready_())
    return;

  if (!this->application_ready_) {
    this->start_connect_if_ready_();
    return;
  }

  this->start_refresh_();
}

void VentilationUnitComponent::loop() {
  if (this->state_ == State::IDLE) {
    if (!this->application_ready_) {
      this->start_connect_if_ready_();
      return;
    }
    this->start_next_command_();
    return;
  }

  switch (this->state_) {
    case State::SENDING:
      this->handle_sending_();
      return;
    case State::RESET_HIGH_WAIT:
      this->handle_reset_high_wait_();
      return;
    case State::RESET_LOW_WAIT:
      this->handle_reset_low_wait_();
      return;
    case State::STARTUP_WAIT:
      this->handle_startup_wait_();
      return;
    case State::WAIT_VERSION:
      this->handle_version_();
      return;
    case State::WAIT_REFRESH:
      this->handle_refresh_();
      return;
    case State::WAIT_WRITE:
      this->handle_write_();
      return;
    case State::WAIT_SAVE:
      this->handle_save_();
      return;
    case State::WAIT_FILTER_RUNTIME_READBACK:
      this->handle_filter_runtime_readback_();
      return;
    case State::IDLE:
      return;
  }
}

void VentilationUnitComponent::queue_write(uint8_t reg, uint16_t value) {
  if (!this->edit_mode_) {
    ESP_LOGW(TAG, "Ignoring write to register 0x%02X because edit mode is disabled", reg);
    return;
  }
  this->queue_command_({reg, value});
}

void VentilationUnitComponent::set_edit_mode(bool enabled) {
  if (this->edit_mode_ == enabled) {
    if (this->edit_mode_switch_ != nullptr)
      this->edit_mode_switch_->publish_state(enabled);
    return;
  }

  this->edit_mode_ = enabled;
  if (!enabled)
    this->command_read_ = this->command_write_;
  if (this->edit_mode_switch_ != nullptr)
    this->edit_mode_switch_->publish_state(enabled);
  ESP_LOGI(TAG, "Edit mode %s", enabled ? LOG_STR_LITERAL("enabled") : LOG_STR_LITERAL("disabled"));
}

bool VentilationUnitComponent::parent_ready_() {
  if (!this->transport_ready_()) {
    ESP_LOGD(TAG, "USB UART is not connected yet");
    return false;
  }
  return true;
}

void VentilationUnitComponent::start_connect_if_ready_() {
  if (!this->transport_ready_() || !this->time_reached_(this->next_connect_attempt_))
    return;

  if (!this->reset_attempted_)
    this->start_app_reset_();
  else
    this->start_register_read_(REG_VERSION, State::WAIT_VERSION);
}

// USB captures of the official app showed one USB transfer per protocol byte;
// bundling a whole command into one transfer can desync the controller's byte
// parser. So each byte is written and flushed on its own, spaced by at least
// INTER_BYTE_DELAY_MS. Bytes are pumped one per loop() iteration instead of
// with a blocking delay: the controller's parser is purely byte-driven and
// tolerates arbitrary gaps between bytes, so this keeps the wire behavior
// identical without blocking the main loop.
void VentilationUnitComponent::begin_send_() {
  this->tx_pos_ = 0;
  this->tx_next_byte_ = millis();  // the first byte may go out on the next loop
  this->state_ = State::SENDING;
}

void VentilationUnitComponent::handle_sending_() {
  if (!this->time_reached_(this->tx_next_byte_))
    return;

  if (this->tx_pos_ < this->tx_len_) {
    this->write_byte(this->tx_buf_[this->tx_pos_++]);
    this->flush();
    this->tx_next_byte_ = millis() + INTER_BYTE_DELAY_MS;
    return;
  }

  // All bytes are on the wire and the trailing inter-byte gap has elapsed.
  if (this->after_send_ == AfterSend::READ) {
    this->start_read_(this->after_read_len_, this->after_timeout_, this->after_state_);
  } else {
    this->wait_until_ = millis() + this->after_timeout_;
    this->state_ = this->after_state_;
  }
}

void VentilationUnitComponent::start_app_reset_() {
  ESP_LOGI(TAG, "Resetting ventilation controller into application");
  this->reset_attempted_ = true;
  this->discard_available();
  // RTS low keeps BOOT0 low. DTR high asserts NRST low.
  this->set_modem_lines_(true, false);
  this->wait_until_ = millis() + RESET_PULSE_MS;
  this->state_ = State::RESET_HIGH_WAIT;
}

void VentilationUnitComponent::handle_reset_high_wait_() {
  if (!this->time_reached_(this->wait_until_))
    return;
  this->set_modem_lines_(false, false);
  this->wait_until_ = millis() + RESET_PULSE_MS;
  this->state_ = State::RESET_LOW_WAIT;
}

void VentilationUnitComponent::handle_reset_low_wait_() {
  if (!this->time_reached_(this->wait_until_))
    return;
  this->discard_available();
  this->wait_until_ = millis() + STARTUP_DELAY_MS;
  this->state_ = State::STARTUP_WAIT;
}

void VentilationUnitComponent::handle_startup_wait_() {
  if (!this->time_reached_(this->wait_until_))
    return;
  this->start_register_read_(REG_VERSION, State::WAIT_VERSION);
}

void VentilationUnitComponent::handle_version_() {
  uint16_t version;
  if (!this->read_u16_response_or_timeout_(REG_VERSION, &version))
    return;

  ESP_LOGI(TAG, "Connected to ventilation firmware v%u.%u", version >> 8, version & 0xFF);
  if (this->firmware_version_text_sensor_ != nullptr) {
    char buffer[12];
    snprintf(buffer, sizeof(buffer), "%u.%u", version >> 8, version & 0xFF);
    this->firmware_version_text_sensor_->publish_state(buffer);
  }
  this->application_ready_ = true;
  this->status_clear_warning();
  this->start_refresh_();
}

void VentilationUnitComponent::start_refresh_() {
  this->refresh_index_ = 0;
  this->start_next_refresh_read_();
}

void VentilationUnitComponent::start_next_refresh_read_() {
  if (this->refresh_index_ >= refresh_register_count_()) {
    this->state_ = State::IDLE;
    return;
  }
  this->start_register_read_(this->refresh_reg_(this->refresh_index_), State::WAIT_REFRESH);
}

void VentilationUnitComponent::handle_refresh_() {
  uint16_t raw;
  if (!this->read_u16_response_or_timeout_(this->current_reg_, &raw))
    return;

  this->publish_register_(this->current_reg_, raw);
  this->refresh_index_++;
  this->start_next_refresh_read_();
}

void VentilationUnitComponent::publish_filter_remaining_() {
  if (this->filter_life_remaining_sensor_ == nullptr && this->filter_remaining_hours_sensor_ == nullptr)
    return;
  if (!this->register_cache_valid_[REG_FILTER_RUNTIME] || !this->register_cache_valid_[REG_FILTER_REPLACEMENT_INTERVAL])
    return;
  const uint16_t runtime = this->register_cache_[REG_FILTER_RUNTIME];
  const uint16_t interval = this->register_cache_[REG_FILTER_REPLACEMENT_INTERVAL];
  const uint16_t remaining = runtime < interval ? interval - runtime : 0;
  if (this->filter_life_remaining_sensor_ != nullptr) {
    const float percent = interval == 0 ? 0.0f : 100.0f * static_cast<float>(remaining) / interval;
    this->filter_life_remaining_sensor_->publish_state(percent);
  }
  if (this->filter_remaining_hours_sensor_ != nullptr)
    this->filter_remaining_hours_sensor_->publish_state(static_cast<float>(remaining) / 6.0f);
}

void VentilationUnitComponent::publish_register_(uint8_t reg, uint16_t raw) {
  if (this->register_cache_valid_[reg] && this->register_cache_[reg] == raw) {
    this->status_clear_warning();
    return;
  }
  this->register_cache_[reg] = raw;
  this->register_cache_valid_[reg] = true;

  if (reg == REG_HUMIDITY_SENSOR_INPUT) {
    if (this->humidity_sensor_ != nullptr)
      this->humidity_sensor_->publish_state(static_cast<float>(raw) / 33.0f);
    if (this->humidity_voltage_sensor_ != nullptr)
      this->humidity_voltage_sensor_->publish_state(static_cast<float>(raw) / 333.0f);
  } else if (reg == REG_TEMPERATURE) {
    if (this->temperature_sensor_ != nullptr)
      this->temperature_sensor_->publish_state(static_cast<float>(raw) - 40.0f);
  } else if (reg == REG_INFLOW_RPM) {
    if (this->inflow_rpm_sensor_ != nullptr)
      this->inflow_rpm_sensor_->publish_state(raw * 60.0f);
  } else if (reg == REG_OUTFLOW_RPM) {
    if (this->outflow_rpm_sensor_ != nullptr)
      this->outflow_rpm_sensor_->publish_state(raw * 60.0f);
  } else if (reg == REG_FORCE_INPUT) {
    if (this->force_input_binary_sensor_ != nullptr)
      this->force_input_binary_sensor_->publish_state(raw != 0);
  } else if (reg == REG_BYPASS) {
    if (this->bypass_binary_sensor_ != nullptr)
      this->bypass_binary_sensor_->publish_state(raw != 0);
  } else if (reg == REG_BYPASS_HARDWARE_PRESENT) {
    this->publish_switch_(this->bypass_hardware_present_switch_, raw);
  } else if (reg == REG_BYPASS_POLARITY_INVERT) {
    this->publish_switch_(this->bypass_polarity_invert_switch_, raw);
  } else if (reg == REG_FILTER_RUNTIME) {
    if (this->filter_runtime_sensor_ != nullptr)
      this->filter_runtime_sensor_->publish_state(static_cast<float>(raw) / 6.0f);
    this->publish_filter_remaining_();
  } else if (reg == REG_FILTER_REPLACEMENT_INTERVAL) {
    this->publish_number_(this->filter_replacement_interval_number_, reg, raw);
    this->publish_filter_remaining_();
  } else if (reg == REG_FREEZE_PROTECTION_THRESHOLD) {
    this->publish_number_(this->freeze_protection_threshold_number_, reg, raw);
  } else if (reg == REG_HUMIDITY_BOOST_THRESHOLD) {
    this->publish_number_(this->humidity_boost_threshold_number_, reg, raw);
  } else if (reg >= REG_INFLOW_SPEED_SETPOINT_BASE && reg < REG_INFLOW_SPEED_SETPOINT_BASE + SETPOINT_COUNT) {
    this->publish_number_(this->inflow_speed_setpoint_numbers_[reg - REG_INFLOW_SPEED_SETPOINT_BASE], reg, raw);
  } else if (reg >= REG_OUTFLOW_SPEED_SETPOINT_BASE && reg < REG_OUTFLOW_SPEED_SETPOINT_BASE + SETPOINT_COUNT) {
    this->publish_number_(this->outflow_speed_setpoint_numbers_[reg - REG_OUTFLOW_SPEED_SETPOINT_BASE], reg, raw);
  }
  this->status_clear_warning();
}

void VentilationUnitComponent::start_register_read_(uint8_t reg, State wait_state) {
  this->current_reg_ = reg;
  this->discard_available();
  this->tx_buf_[0] = 0xFF;
  this->tx_buf_[1] = 0x01;
  this->tx_buf_[2] = reg;
  this->tx_len_ = 3;
  this->after_send_ = AfterSend::READ;
  this->after_read_len_ = 2;
  this->after_timeout_ = RESPONSE_TIMEOUT_MS;
  this->after_state_ = wait_state;
  this->begin_send_();
}

void VentilationUnitComponent::start_register_write_(uint8_t reg, uint16_t value, State wait_state) {
  this->tx_buf_[0] = 0xFF;
  this->tx_buf_[1] = 0x00;
  this->tx_buf_[2] = reg;
  this->tx_buf_[3] = (value >> 8) & 0xFF;
  this->tx_buf_[4] = value & 0xFF;
  this->tx_len_ = 5;
  this->after_send_ = AfterSend::DELAY;
  this->after_timeout_ = 50;
  this->after_state_ = wait_state;
  this->begin_send_();
}

void VentilationUnitComponent::handle_write_() {
  if (!this->time_reached_(this->wait_until_))
    return;
  // Register writes only update RAM. Reading 0x60 is the firmware's flash
  // commit trigger, matching the official app's "Write Config" action.
  this->start_register_read_(REG_COMMIT_CONFIG_TO_FLASH, State::WAIT_SAVE);
}

void VentilationUnitComponent::handle_save_() {
  uint16_t ignored;
  if (!this->read_u16_response_or_timeout_(REG_COMMIT_CONFIG_TO_FLASH, &ignored))
    return;
  ESP_LOGI(TAG, "Configuration saved");
  if (this->current_command_.reg == REG_FILTER_REPLACEMENT_RESET) {
    this->start_register_read_(REG_FILTER_RUNTIME, State::WAIT_FILTER_RUNTIME_READBACK);
    return;
  }
  this->publish_register_(this->current_command_.reg, this->current_command_.value);
  this->state_ = State::IDLE;
}

void VentilationUnitComponent::handle_filter_runtime_readback_() {
  uint16_t raw;
  if (!this->read_u16_response_or_timeout_(REG_FILTER_RUNTIME, &raw))
    return;
  this->publish_register_(REG_FILTER_RUNTIME, raw);
  this->state_ = State::IDLE;
}

void VentilationUnitComponent::queue_command_(Command command) {
  uint8_t next = (this->command_write_ + 1) % COMMAND_QUEUE_SIZE;
  if (next == this->command_read_) {
    ESP_LOGW(TAG, "Command queue full; dropping register 0x%02X", command.reg);
    return;
  }
  this->command_queue_[this->command_write_] = command;
  this->command_write_ = next;
}

void VentilationUnitComponent::start_next_command_() {
  if (!this->application_ready_ || this->command_read_ == this->command_write_)
    return;
  if (!this->edit_mode_) {
    ESP_LOGW(TAG, "Dropping pending configuration writes because edit mode is disabled");
    this->command_read_ = this->command_write_;
    return;
  }
  this->current_command_ = this->command_queue_[this->command_read_];
  this->command_read_ = (this->command_read_ + 1) % COMMAND_QUEUE_SIZE;
  this->start_register_write_(this->current_command_.reg, this->current_command_.value);
}

void VentilationUnitComponent::start_read_(size_t len, uint32_t timeout_ms, State wait_state) {
  this->response_pos_ = 0;
  this->response_len_ = len;
  this->deadline_ = millis() + timeout_ms;
  this->state_ = wait_state;
}

bool VentilationUnitComponent::read_u16_response_or_timeout_(uint8_t reg, uint16_t *value) {
  this->pump_response_();
  if (this->response_pos_ >= 2) {
    *value = (static_cast<uint16_t>(this->response_[0]) << 8) | this->response_[1];
    return true;
  }
  if (!this->timed_out_())
    return false;

  ESP_LOGW(TAG, "Application firmware did not answer register 0x%02X", reg);
  this->status_set_warning();
  this->mark_application_lost_();
  return false;
}

void VentilationUnitComponent::mark_application_lost_() {
  if (this->application_ready_) {
    ESP_LOGW(TAG, "Lost communication with ventilation controller; reconnecting");
  }
  this->application_ready_ = false;
  this->reset_attempted_ = false;
  this->next_connect_attempt_ = millis() + 2000;
  this->command_read_ = this->command_write_;
  this->state_ = State::IDLE;
}

void VentilationUnitComponent::pump_response_() {
  while (this->response_pos_ < this->response_len_ && this->available())
    this->response_[this->response_pos_++] = this->read();
}

void VentilationUnitComponent::set_modem_lines_(bool dtr, bool rts) {
#ifdef USE_HOST
  auto *channel = static_cast<uart::HostUartComponent *>(this->parent_);
#else
  auto *channel = static_cast<usb_uart::USBUartChannelBase *>(this->parent_);
#endif
  ESP_LOGD(TAG, "Modem lines: DTR=%u RTS=%u", dtr, rts);
  if (!channel->set_modem_control(dtr, rts)) {
    ESP_LOGW(TAG, "USB serial not connected; DTR/RTS not set");
  }
}

}  // namespace ventilation_unit
}  // namespace esphome
