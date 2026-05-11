#pragma once

#include "esphome/components/button/button.h"
#include "esphome/components/binary_sensor/binary_sensor.h"
#include "esphome/components/number/number.h"
#include "esphome/components/sensor/sensor.h"
#include "esphome/components/switch/switch.h"
#include "esphome/components/text_sensor/text_sensor.h"
#include "esphome/components/uart/uart.h"
#include "esphome/components/usb_host/usb_host.h"
#include "esphome/components/usb_uart/usb_uart.h"
#include "esphome/core/component.h"
#include "esphome/core/log.h"
#include <cstdio>

namespace esphome {
namespace ventilation_unit {

class VentilationUnitComponent;

class VentilationUnitNumber : public number::Number {
 public:
  void set_parent(VentilationUnitComponent *parent) { parent_ = parent; }
  void set_register(uint8_t reg) { reg_ = reg; }
  void set_scale(float scale) { scale_ = scale; }
  void set_signed(bool signed_value) { signed_ = signed_value; }

  uint8_t get_register() const { return reg_; }
  float from_raw(uint16_t raw) const {
    if (signed_)
      return static_cast<float>(static_cast<int16_t>(raw)) / scale_;
    return static_cast<float>(raw) / scale_;
  }

 protected:
  void control(float value) override;

  VentilationUnitComponent *parent_{nullptr};
  uint8_t reg_{0};
  float scale_{1.0f};
  bool signed_{false};
};

class VentilationUnitSwitch : public switch_::Switch {
 public:
  void set_parent(VentilationUnitComponent *parent) { parent_ = parent; }
  void set_register(uint8_t reg) { reg_ = reg; }

 protected:
  void write_state(bool state) override;

  VentilationUnitComponent *parent_{nullptr};
  uint8_t reg_{0};
};

class VentilationUnitEditModeSwitch : public switch_::Switch {
 public:
  void set_parent(VentilationUnitComponent *parent) { parent_ = parent; }

 protected:
  void write_state(bool state) override;

  VentilationUnitComponent *parent_{nullptr};
};

class VentilationUnitButton : public button::Button {
 public:
  void set_parent(VentilationUnitComponent *parent) { parent_ = parent; }
  void set_register(uint8_t reg) { reg_ = reg; }
  void set_value(uint16_t value) { value_ = value; }

 protected:
  void press_action() override;

  VentilationUnitComponent *parent_{nullptr};
  uint8_t reg_{0};
  uint16_t value_{1};
};

class VentilationUnitComponent : public PollingComponent, public uart::UARTDevice {
 public:
  void set_temperature_sensor(sensor::Sensor *sensor) { temperature_sensor_ = sensor; }
  void set_humidity_sensor(sensor::Sensor *sensor) { humidity_sensor_ = sensor; }
  void set_humidity_voltage_sensor(sensor::Sensor *sensor) { humidity_voltage_sensor_ = sensor; }
  void set_inflow_rpm_sensor(sensor::Sensor *sensor) { inflow_rpm_sensor_ = sensor; }
  void set_outflow_rpm_sensor(sensor::Sensor *sensor) { outflow_rpm_sensor_ = sensor; }
  void set_force_input_binary_sensor(binary_sensor::BinarySensor *sensor) { force_input_binary_sensor_ = sensor; }
  void set_bypass_binary_sensor(binary_sensor::BinarySensor *sensor) { bypass_binary_sensor_ = sensor; }
  void set_edit_mode_switch(VentilationUnitEditModeSwitch *switch_) { edit_mode_switch_ = switch_; }
  void set_bypass_hardware_present_switch(VentilationUnitSwitch *switch_) { bypass_hardware_present_switch_ = switch_; }
  void set_bypass_polarity_invert_switch(VentilationUnitSwitch *switch_) { bypass_polarity_invert_switch_ = switch_; }
  void set_filter_runtime_sensor(sensor::Sensor *sensor) { filter_runtime_sensor_ = sensor; }
  void set_filter_replacement_interval_number(VentilationUnitNumber *number) {
    filter_replacement_interval_number_ = number;
  }
  void set_filter_replacement_reset_button(VentilationUnitButton *button) {
    filter_replacement_reset_button_ = button;
  }
  void set_freeze_protection_threshold_number(VentilationUnitNumber *number) {
    freeze_protection_threshold_number_ = number;
  }
  void set_humidity_boost_threshold_number(VentilationUnitNumber *number) {
    humidity_boost_threshold_number_ = number;
  }
  void set_inflow_speed_setpoint_number(uint8_t index,
                                        VentilationUnitNumber *number) {
    if (index < SETPOINT_COUNT)
      inflow_speed_setpoint_numbers_[index] = number;
  }
  void set_outflow_speed_setpoint_number(uint8_t index,
                                         VentilationUnitNumber *number) {
    if (index < SETPOINT_COUNT)
      outflow_speed_setpoint_numbers_[index] = number;
  }
  void set_firmware_version_text_sensor(text_sensor::TextSensor *sensor) { firmware_version_text_sensor_ = sensor; }

  void setup() override {
    ESP_LOGCONFIG(TAG, "Ventilation unit ready");
    if (this->edit_mode_switch_ != nullptr)
      this->edit_mode_switch_->publish_state(this->edit_mode_);
  }

  void dump_config() override {
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
    LOG_NUMBER("  ", "Filter replacement interval", this->filter_replacement_interval_number_);
    LOG_BUTTON("  ", "Filter replacement reset", this->filter_replacement_reset_button_);
    LOG_NUMBER("  ", "Freeze protection threshold", this->freeze_protection_threshold_number_);
    LOG_NUMBER("  ", "Humidity boost threshold", this->humidity_boost_threshold_number_);
    LOG_TEXT_SENSOR("  ", "Firmware version", this->firmware_version_text_sensor_);
  }

  void update() override {
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

  void loop() override {
    if (this->state_ == State::IDLE) {
      if (!this->application_ready_) {
        this->start_connect_if_ready_();
        return;
      }
      this->start_next_command_();
      return;
    }

    switch (this->state_) {
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

  void queue_write(uint8_t reg, uint16_t value) {
    if (!this->edit_mode_) {
      ESP_LOGW(TAG, "Ignoring write to register 0x%02X because edit mode is disabled", reg);
      return;
    }
    this->queue_command_({reg, value});
  }

  void set_edit_mode(bool enabled) {
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
    ESP_LOGI(TAG, "Edit mode %s", enabled ? "enabled" : "disabled");
  }

 protected:
  enum class State : uint8_t {
    IDLE,
    RESET_HIGH_WAIT,
    RESET_LOW_WAIT,
    STARTUP_WAIT,
    WAIT_VERSION,
    WAIT_REFRESH,
    WAIT_WRITE,
    WAIT_SAVE,
    WAIT_FILTER_RUNTIME_READBACK,
  };

  struct Command {
    uint8_t reg;
    uint16_t value;
  };

  static constexpr const char *TAG = "ventilation_unit";
  static constexpr uint8_t SETPOINT_COUNT = 6;
  static constexpr uint8_t COMMAND_QUEUE_SIZE = 8;
  static constexpr uint8_t REG_INFLOW_SPEED_SETPOINT_BASE = 0x10;
  static constexpr uint8_t REG_OUTFLOW_SPEED_SETPOINT_BASE = 0x20;
  static constexpr uint8_t REG_BYPASS = 0x30;
  static constexpr uint8_t REG_BYPASS_HARDWARE_PRESENT = 0x31;
  static constexpr uint8_t REG_BYPASS_POLARITY_INVERT = 0x32;
  static constexpr uint8_t REG_INFLOW_RPM = 0x40;
  static constexpr uint8_t REG_OUTFLOW_RPM = 0x41;
  static constexpr uint8_t REG_HUMIDITY_SENSOR_INPUT = 0x50;
  static constexpr uint8_t REG_TEMPERATURE = 0x51;
  static constexpr uint8_t REG_FORCE_INPUT = 0x52;
  static constexpr uint8_t REG_FILTER_RUNTIME = 0x53;
  static constexpr uint8_t REG_FILTER_REPLACEMENT_RESET = 0x54;
  static constexpr uint8_t REG_FILTER_REPLACEMENT_INTERVAL = 0x55;
  static constexpr uint8_t REG_COMMIT_CONFIG_TO_FLASH = 0x60;
  static constexpr uint8_t REG_FREEZE_PROTECTION_THRESHOLD = 0x70;
  static constexpr uint8_t REG_HUMIDITY_BOOST_THRESHOLD = 0x72;
  static constexpr uint8_t REG_VERSION = 0xFF;
  static constexpr uint8_t CP210X_SET_MHS = 0x07;
  static constexpr uint16_t CP210X_CONTROL_DTR = 0x0001;
  static constexpr uint16_t CP210X_CONTROL_RTS = 0x0002;
  static constexpr uint16_t CP210X_CONTROL_WRITE_DTR = 0x0100;
  static constexpr uint16_t CP210X_CONTROL_WRITE_RTS = 0x0200;
  static constexpr uint32_t INTER_BYTE_DELAY_MS = 2;
  static constexpr uint32_t RESPONSE_TIMEOUT_MS = 2000;
  static constexpr uint32_t RESET_PULSE_MS = 400;
  static constexpr uint32_t STARTUP_DELAY_MS = 800;
  static constexpr uint8_t REFRESH_REGS[] = {
      REG_HUMIDITY_SENSOR_INPUT,           // 0-10 V humidity input
      REG_TEMPERATURE,                     // Temperature, encoded as C + 40
      REG_INFLOW_RPM,                      // Inflow RPM at PPR=1
      REG_OUTFLOW_RPM,                     // Outflow RPM at PPR=1
      REG_FORCE_INPUT,                     // Force input
      REG_BYPASS,                          // Bypass
      REG_BYPASS_HARDWARE_PRESENT,         // Bypass hardware present
      REG_BYPASS_POLARITY_INVERT,          // Bypass polarity invert
      REG_FILTER_RUNTIME,                  // Filter runtime
      REG_FILTER_REPLACEMENT_INTERVAL,     // Filter replacement interval
      REG_FREEZE_PROTECTION_THRESHOLD,     // Freeze protection threshold
      REG_HUMIDITY_BOOST_THRESHOLD,        // Humidity boost threshold
      REG_INFLOW_SPEED_SETPOINT_BASE + 0,   // Inflow standby setpoint
      REG_INFLOW_SPEED_SETPOINT_BASE + 1,   // Inflow speed 1 setpoint
      REG_INFLOW_SPEED_SETPOINT_BASE + 2,   // Inflow speed 2 setpoint
      REG_INFLOW_SPEED_SETPOINT_BASE + 3,   // Inflow speed 3 setpoint
      REG_INFLOW_SPEED_SETPOINT_BASE + 4,   // Inflow force input setpoint
      REG_INFLOW_SPEED_SETPOINT_BASE + 5,   // Inflow humidity boost setpoint
      REG_OUTFLOW_SPEED_SETPOINT_BASE + 0,  // Outflow standby setpoint
      REG_OUTFLOW_SPEED_SETPOINT_BASE + 1,  // Outflow speed 1 setpoint
      REG_OUTFLOW_SPEED_SETPOINT_BASE + 2,  // Outflow speed 2 setpoint
      REG_OUTFLOW_SPEED_SETPOINT_BASE + 3,  // Outflow speed 3 setpoint
      REG_OUTFLOW_SPEED_SETPOINT_BASE + 4,  // Outflow force input setpoint
      REG_OUTFLOW_SPEED_SETPOINT_BASE + 5,  // Outflow humidity boost setpoint
  };

  sensor::Sensor *temperature_sensor_{nullptr};
  sensor::Sensor *humidity_sensor_{nullptr};
  sensor::Sensor *humidity_voltage_sensor_{nullptr};
  sensor::Sensor *inflow_rpm_sensor_{nullptr};
  sensor::Sensor *outflow_rpm_sensor_{nullptr};
  binary_sensor::BinarySensor *force_input_binary_sensor_{nullptr};
  binary_sensor::BinarySensor *bypass_binary_sensor_{nullptr};
  VentilationUnitEditModeSwitch *edit_mode_switch_{nullptr};
  VentilationUnitSwitch *bypass_hardware_present_switch_{nullptr};
  VentilationUnitSwitch *bypass_polarity_invert_switch_{nullptr};
  sensor::Sensor *filter_runtime_sensor_{nullptr};
  VentilationUnitNumber *filter_replacement_interval_number_{nullptr};
  VentilationUnitButton *filter_replacement_reset_button_{nullptr};
  VentilationUnitNumber *freeze_protection_threshold_number_{nullptr};
  VentilationUnitNumber *humidity_boost_threshold_number_{nullptr};
  VentilationUnitNumber *inflow_speed_setpoint_numbers_[SETPOINT_COUNT]{};
  VentilationUnitNumber *outflow_speed_setpoint_numbers_[SETPOINT_COUNT]{};
  text_sensor::TextSensor *firmware_version_text_sensor_{nullptr};
  bool edit_mode_{false};
  bool application_ready_{false};
  bool reset_attempted_{false};
  uint32_t next_connect_attempt_{0};
  State state_{State::IDLE};
  uint32_t deadline_{0};
  uint32_t wait_until_{0};
  uint8_t response_[81]{};
  size_t response_pos_{0};
  size_t response_len_{0};
  uint8_t current_reg_{0};
  uint8_t refresh_index_{0};
  uint16_t register_cache_[256]{};
  bool register_cache_valid_[256]{};
  Command command_queue_[COMMAND_QUEUE_SIZE]{};
  uint8_t command_read_{0};
  uint8_t command_write_{0};
  Command current_command_{};

  bool parent_ready_() {
    if (!this->transport_ready_()) {
      ESP_LOGD(TAG, "USB UART is not connected yet");
      return false;
    }
    return true;
  }

  bool transport_ready_() const { return this->parent_ != nullptr && this->parent_->is_connected(); }

  void start_connect_if_ready_() {
    if (!this->transport_ready_() || !this->time_reached_(this->next_connect_attempt_))
      return;

    if (!this->reset_attempted_)
      this->start_app_reset_();
    else
      this->start_register_read_(REG_VERSION, State::WAIT_VERSION);
  }

  void write_byte_slow_(uint8_t byte) {
    // USB captures of the official app showed one transfer per protocol byte.
    // Sending a whole command buffer can desync the unit firmware's parser.
    this->write_byte(byte);
    this->flush();
    delay(INTER_BYTE_DELAY_MS);
  }

  void start_app_reset_() {
    ESP_LOGI(TAG, "Resetting ventilation controller into application");
    this->reset_attempted_ = true;
    this->drain_();
    // RTS low keeps BOOT0 low. DTR high asserts NRST low.
    this->set_cp210x_modem_(true, false);
    this->wait_until_ = millis() + RESET_PULSE_MS;
    this->state_ = State::RESET_HIGH_WAIT;
  }

  void handle_reset_high_wait_() {
    if (!this->time_reached_(this->wait_until_))
      return;
    this->set_cp210x_modem_(false, false);
    this->wait_until_ = millis() + RESET_PULSE_MS;
    this->state_ = State::RESET_LOW_WAIT;
  }

  void handle_reset_low_wait_() {
    if (!this->time_reached_(this->wait_until_))
      return;
    this->drain_();
    this->wait_until_ = millis() + STARTUP_DELAY_MS;
    this->state_ = State::STARTUP_WAIT;
  }

  void handle_startup_wait_() {
    if (!this->time_reached_(this->wait_until_))
      return;
    this->start_register_read_(REG_VERSION, State::WAIT_VERSION);
  }

  void handle_version_() {
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

  void start_refresh_() {
    this->refresh_index_ = 0;
    this->start_next_refresh_read_();
  }

  void start_next_refresh_read_() {
    if (this->refresh_index_ >= refresh_register_count_()) {
      this->state_ = State::IDLE;
      return;
    }
    this->start_register_read_(this->refresh_reg_(this->refresh_index_), State::WAIT_REFRESH);
  }

  uint8_t refresh_reg_(uint8_t index) const {
    if (index < refresh_register_count_())
      return REFRESH_REGS[index];
    return REG_VERSION;
  }

  static constexpr size_t refresh_register_count_() {
    return sizeof(REFRESH_REGS) / sizeof(REFRESH_REGS[0]);
  }

  void handle_refresh_() {
    uint16_t raw;
    if (!this->read_u16_response_or_timeout_(this->current_reg_, &raw))
      return;

    this->publish_register_(this->current_reg_, raw);
    this->refresh_index_++;
    this->start_next_refresh_read_();
  }

  void publish_register_(uint8_t reg, uint16_t raw) {
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
    } else if (reg == REG_FILTER_REPLACEMENT_INTERVAL) {
      this->publish_number_(this->filter_replacement_interval_number_, raw);
    } else if (reg == REG_FREEZE_PROTECTION_THRESHOLD) {
      this->publish_number_(this->freeze_protection_threshold_number_, raw);
    } else if (reg == REG_HUMIDITY_BOOST_THRESHOLD) {
      this->publish_number_(this->humidity_boost_threshold_number_, raw);
    } else if (reg >= REG_INFLOW_SPEED_SETPOINT_BASE &&
               reg < REG_INFLOW_SPEED_SETPOINT_BASE + SETPOINT_COUNT) {
      this->publish_number_(this->inflow_speed_setpoint_numbers_[reg - REG_INFLOW_SPEED_SETPOINT_BASE], raw);
    } else if (reg >= REG_OUTFLOW_SPEED_SETPOINT_BASE &&
               reg < REG_OUTFLOW_SPEED_SETPOINT_BASE + SETPOINT_COUNT) {
      this->publish_number_(this->outflow_speed_setpoint_numbers_[reg - REG_OUTFLOW_SPEED_SETPOINT_BASE], raw);
    }
    this->status_clear_warning();
  }

  void publish_number_(VentilationUnitNumber *number, uint16_t raw) {
    if (number != nullptr)
      number->publish_state(number->from_raw(raw));
  }

  void publish_switch_(VentilationUnitSwitch *switch_, uint16_t raw) {
    if (switch_ != nullptr)
      switch_->publish_state(raw != 0);
  }

  void start_register_read_(uint8_t reg, State wait_state) {
    this->current_reg_ = reg;
    this->drain_();
    this->write_byte_slow_(0xFF);
    this->write_byte_slow_(0x01);
    this->write_byte_slow_(reg);
    this->start_read_(2, RESPONSE_TIMEOUT_MS, wait_state);
  }

  void start_register_write_(uint8_t reg, uint16_t value, State wait_state = State::WAIT_WRITE) {
    this->write_byte_slow_(0xFF);
    this->write_byte_slow_(0x00);
    this->write_byte_slow_(reg);
    this->write_byte_slow_((value >> 8) & 0xFF);
    this->write_byte_slow_(value & 0xFF);
    this->wait_until_ = millis() + 50;
    this->state_ = wait_state;
  }

  void handle_write_() {
    if (!this->time_reached_(this->wait_until_))
      return;
    // Register writes only update RAM. Reading 0x60 is the firmware's flash
    // commit trigger, matching the official app's "Write Config" action.
    this->start_register_read_(REG_COMMIT_CONFIG_TO_FLASH, State::WAIT_SAVE);
  }

  void handle_save_() {
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

  void handle_filter_runtime_readback_() {
    uint16_t raw;
    if (!this->read_u16_response_or_timeout_(REG_FILTER_RUNTIME, &raw))
      return;
    this->publish_register_(REG_FILTER_RUNTIME, raw);
    this->state_ = State::IDLE;
  }

  void queue_command_(Command command) {
    uint8_t next = (this->command_write_ + 1) % COMMAND_QUEUE_SIZE;
    if (next == this->command_read_) {
      ESP_LOGW(TAG, "Command queue full; dropping register 0x%02X", command.reg);
      return;
    }
    this->command_queue_[this->command_write_] = command;
    this->command_write_ = next;
  }

  void start_next_command_() {
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

  void start_read_(size_t len, uint32_t timeout_ms, State wait_state) {
    this->response_pos_ = 0;
    this->response_len_ = len;
    this->deadline_ = millis() + timeout_ms;
    this->state_ = wait_state;
  }

  bool read_u16_response_or_timeout_(uint8_t reg, uint16_t *value) {
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

  void mark_application_lost_() {
    if (this->application_ready_)
      ESP_LOGW(TAG, "Lost communication with ventilation controller; reconnecting");
    this->application_ready_ = false;
    this->reset_attempted_ = false;
    this->next_connect_attempt_ = millis() + 2000;
    this->command_read_ = this->command_write_;
    this->state_ = State::IDLE;
  }

  void pump_response_() {
    while (this->response_pos_ < this->response_len_ && this->available())
      this->response_[this->response_pos_++] = this->read();
  }

  bool timed_out_() const { return this->time_reached_(this->deadline_); }

  bool time_reached_(uint32_t deadline) const { return static_cast<int32_t>(millis() - deadline) >= 0; }

  void set_cp210x_modem_(bool dtr, bool rts) {
#if defined(USE_ESP32_VARIANT_ESP32P4) || defined(USE_ESP32_VARIANT_ESP32S2) || defined(USE_ESP32_VARIANT_ESP32S3)
    auto *channel = static_cast<usb_uart::USBUartChannel *>(this->parent_);
    auto *usb = channel->get_parent();
    if (usb == nullptr)
      return;

    uint16_t value = CP210X_CONTROL_WRITE_DTR | CP210X_CONTROL_WRITE_RTS;
    if (dtr)
      value |= CP210X_CONTROL_DTR;
    if (rts)
      value |= CP210X_CONTROL_RTS;

    usb_host::transfer_cb_t callback = [](const usb_host::TransferStatus &status) {
      if (!status.success)
        ESP_LOGW(TAG, "CP210x modem control transfer failed: %s", esp_err_to_name(status.error_code));
    };
    usb->control_transfer(usb_uart::USB_VENDOR_IFC | usb_host::USB_DIR_OUT, CP210X_SET_MHS, value, 0, callback);
#endif
  }

  void drain_() {
    while (this->available())
      this->read();
  }
};

inline void VentilationUnitNumber::control(float value) {
  if (this->parent_ == nullptr)
    return;
  if (this->signed_) {
    this->parent_->queue_write(this->reg_, static_cast<uint16_t>(static_cast<int16_t>(value * this->scale_)));
  } else {
    this->parent_->queue_write(this->reg_, static_cast<uint16_t>(value * this->scale_));
  }
}

inline void VentilationUnitSwitch::write_state(bool state) {
  if (this->parent_ == nullptr)
    return;
  this->parent_->queue_write(this->reg_, state ? 1 : 0);
}

inline void VentilationUnitEditModeSwitch::write_state(bool state) {
  if (this->parent_ == nullptr)
    return;
  this->parent_->set_edit_mode(state);
}

inline void VentilationUnitButton::press_action() {
  if (this->parent_ == nullptr)
    return;
  this->parent_->queue_write(this->reg_, this->value_);
}

}  // namespace ventilation_unit
}  // namespace esphome
