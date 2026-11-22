#pragma once

#include "esphome/components/button/button.h"
#include "esphome/components/binary_sensor/binary_sensor.h"
#include "esphome/components/number/number.h"
#include "esphome/components/sensor/sensor.h"
#include "esphome/components/switch/switch.h"
#include "esphome/components/text_sensor/text_sensor.h"
#include "esphome/components/uart/uart.h"
#ifdef USE_HOST
#include "esphome/components/uart/uart_component_host.h"
#else
#include "esphome/components/usb_uart/usb_uart.h"
#endif
#include "esphome/core/component.h"
#include <array>

namespace esphome {
namespace ventilation_unit {

class VentilationUnitComponent final : public PollingComponent, public uart::UARTDevice {
 public:
  void set_temperature_sensor(sensor::Sensor *sensor) { this->temperature_sensor_ = sensor; }
  void set_humidity_sensor(sensor::Sensor *sensor) { this->humidity_sensor_ = sensor; }
  void set_humidity_voltage_sensor(sensor::Sensor *sensor) { this->humidity_voltage_sensor_ = sensor; }
  void set_inflow_rpm_sensor(sensor::Sensor *sensor) { this->inflow_rpm_sensor_ = sensor; }
  void set_outflow_rpm_sensor(sensor::Sensor *sensor) { this->outflow_rpm_sensor_ = sensor; }
  void set_force_input_binary_sensor(binary_sensor::BinarySensor *sensor) { this->force_input_binary_sensor_ = sensor; }
  void set_bypass_binary_sensor(binary_sensor::BinarySensor *sensor) { this->bypass_binary_sensor_ = sensor; }
  void set_edit_mode_switch(switch_::Switch *switch_) { this->edit_mode_switch_ = switch_; }
  void set_bypass_hardware_present_switch(switch_::Switch *switch_) { this->bypass_hardware_present_switch_ = switch_; }
  void set_bypass_polarity_invert_switch(switch_::Switch *switch_) { this->bypass_polarity_invert_switch_ = switch_; }
  void set_filter_runtime_sensor(sensor::Sensor *sensor) { this->filter_runtime_sensor_ = sensor; }
  void set_filter_life_remaining_sensor(sensor::Sensor *sensor) { this->filter_life_remaining_sensor_ = sensor; }
  void set_filter_remaining_hours_sensor(sensor::Sensor *sensor) { this->filter_remaining_hours_sensor_ = sensor; }
  void set_filter_replacement_interval_number(number::Number *number) {
    this->filter_replacement_interval_number_ = number;
  }
  void set_filter_replacement_reset_button(button::Button *button) { this->filter_replacement_reset_button_ = button; }
  void set_freeze_protection_threshold_number(number::Number *number) {
    this->freeze_protection_threshold_number_ = number;
  }
  void set_humidity_boost_threshold_number(number::Number *number) { this->humidity_boost_threshold_number_ = number; }
  void set_inflow_speed_setpoint_number(uint8_t index, number::Number *number) {
    if (index < SETPOINT_COUNT)
      this->inflow_speed_setpoint_numbers_[index] = number;
  }
  void set_outflow_speed_setpoint_number(uint8_t index, number::Number *number) {
    if (index < SETPOINT_COUNT)
      this->outflow_speed_setpoint_numbers_[index] = number;
  }
  void set_firmware_version_text_sensor(text_sensor::TextSensor *sensor) {
    this->firmware_version_text_sensor_ = sensor;
  }

  void setup() override;
  void dump_config() override;
  void update() override;
  void loop() override;

  // A number entity's control: scale the displayed value to the register's raw units and queue it.
  void write_number(uint8_t reg, float value) {
    this->queue_write(reg, static_cast<uint16_t>(value * number_scale_(reg)));
  }

  void queue_write(uint8_t reg, uint16_t value);
  void set_edit_mode(bool enabled);

 protected:
  enum class State : uint8_t {
    IDLE,
    SENDING,
    RESET_HIGH_WAIT,
    RESET_LOW_WAIT,
    STARTUP_WAIT,
    WAIT_VERSION,
    WAIT_REFRESH,
    WAIT_WRITE,
    WAIT_SAVE,
    WAIT_FILTER_RUNTIME_READBACK,
  };

  // What to do once the outgoing byte sequence has fully drained onto the wire.
  enum class AfterSend : uint8_t { READ, DELAY };

  struct Command {
    uint8_t reg;
    uint16_t value;
  };

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
  static constexpr uint32_t INTER_BYTE_DELAY_MS = 2;
  static constexpr uint32_t RESPONSE_TIMEOUT_MS = 2000;
  static constexpr uint32_t RESET_PULSE_MS = 400;
  static constexpr uint32_t STARTUP_DELAY_MS = 800;
  static constexpr uint8_t REFRESH_REGS[] = {
      REG_HUMIDITY_SENSOR_INPUT,            // 0-10 V humidity input
      REG_TEMPERATURE,                      // Temperature, encoded as C + 40
      REG_INFLOW_RPM,                       // Inflow RPM at PPR=1
      REG_OUTFLOW_RPM,                      // Outflow RPM at PPR=1
      REG_FORCE_INPUT,                      // Force input
      REG_BYPASS,                           // Bypass
      REG_BYPASS_HARDWARE_PRESENT,          // Bypass hardware present
      REG_BYPASS_POLARITY_INVERT,           // Bypass polarity invert
      REG_FILTER_RUNTIME,                   // Filter runtime
      REG_FILTER_REPLACEMENT_INTERVAL,      // Filter replacement interval
      REG_FREEZE_PROTECTION_THRESHOLD,      // Freeze protection threshold
      REG_HUMIDITY_BOOST_THRESHOLD,         // Humidity boost threshold
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
  switch_::Switch *edit_mode_switch_{nullptr};
  switch_::Switch *bypass_hardware_present_switch_{nullptr};
  switch_::Switch *bypass_polarity_invert_switch_{nullptr};
  sensor::Sensor *filter_runtime_sensor_{nullptr};
  sensor::Sensor *filter_life_remaining_sensor_{nullptr};
  sensor::Sensor *filter_remaining_hours_sensor_{nullptr};
  number::Number *filter_replacement_interval_number_{nullptr};
  button::Button *filter_replacement_reset_button_{nullptr};
  number::Number *freeze_protection_threshold_number_{nullptr};
  number::Number *humidity_boost_threshold_number_{nullptr};
  std::array<number::Number *, SETPOINT_COUNT> inflow_speed_setpoint_numbers_{};
  std::array<number::Number *, SETPOINT_COUNT> outflow_speed_setpoint_numbers_{};
  text_sensor::TextSensor *firmware_version_text_sensor_{nullptr};
  bool edit_mode_{false};
  bool application_ready_{false};
  bool reset_attempted_{false};
  uint32_t next_connect_attempt_{0};
  State state_{State::IDLE};
  uint32_t deadline_{0};
  uint32_t wait_until_{0};
  std::array<uint8_t, 81> response_{};
  size_t response_pos_{0};
  size_t response_len_{0};
  uint8_t current_reg_{0};
  uint8_t refresh_index_{0};
  std::array<uint16_t, 256> register_cache_{};
  std::array<bool, 256> register_cache_valid_{};
  std::array<Command, COMMAND_QUEUE_SIZE> command_queue_{};
  uint8_t command_read_{0};
  uint8_t command_write_{0};
  Command current_command_{};
  std::array<uint8_t, 5> tx_buf_{};
  uint8_t tx_len_{0};
  uint8_t tx_pos_{0};
  uint32_t tx_next_byte_{0};
  AfterSend after_send_{AfterSend::READ};
  size_t after_read_len_{0};
  uint32_t after_timeout_{0};
  State after_state_{State::IDLE};

  bool parent_ready_();

  bool transport_ready_() const { return this->parent_ != nullptr && this->parent_->is_connected(); }

  void start_connect_if_ready_();

  void begin_send_();
  void handle_sending_();
  void start_app_reset_();
  void handle_reset_high_wait_();
  void handle_reset_low_wait_();
  void handle_startup_wait_();
  void handle_version_();
  void start_refresh_();
  void start_next_refresh_read_();

  uint8_t refresh_reg_(uint8_t index) const {
    if (index < refresh_register_count_())
      return REFRESH_REGS[index];
    return REG_VERSION;
  }

  static constexpr size_t refresh_register_count_() { return sizeof(REFRESH_REGS) / sizeof(REFRESH_REGS[0]); }

  void handle_refresh_();

  // Derived from the controller's own counter (0x53) and interval (0x55), so it agrees with the
  // service-due flag: due exactly when runtime >= interval. Like that flag, it jumps back up if the
  // 16-bit counter wraps (see docs/PROTOCOL.md).
  void publish_filter_remaining_();

  void publish_register_(uint8_t reg, uint16_t raw);

  // Raw register units per displayed number unit: speed setpoints are 0-1000 for 0-100 %, the filter
  // interval counts 10-minute ticks (6 per hour), and the thresholds are stored as-is.
  static constexpr float number_scale_(uint8_t reg) {
    if (reg == REG_FILTER_REPLACEMENT_INTERVAL)
      return 6.0f;
    if ((reg >= REG_INFLOW_SPEED_SETPOINT_BASE && reg < REG_INFLOW_SPEED_SETPOINT_BASE + SETPOINT_COUNT) ||
        (reg >= REG_OUTFLOW_SPEED_SETPOINT_BASE && reg < REG_OUTFLOW_SPEED_SETPOINT_BASE + SETPOINT_COUNT))
      return 10.0f;
    return 1.0f;
  }

  void publish_number_(number::Number *number, uint8_t reg, uint16_t raw) {
    if (number != nullptr)
      number->publish_state(static_cast<float>(raw) / number_scale_(reg));
  }

  void publish_switch_(switch_::Switch *switch_, uint16_t raw) {
    if (switch_ != nullptr)
      switch_->publish_state(raw != 0);
  }

  void start_register_read_(uint8_t reg, State wait_state);
  void start_register_write_(uint8_t reg, uint16_t value, State wait_state = State::WAIT_WRITE);
  void handle_write_();
  void handle_save_();
  void handle_filter_runtime_readback_();
  void queue_command_(Command command);
  void start_next_command_();
  void start_read_(size_t len, uint32_t timeout_ms, State wait_state);
  bool read_u16_response_or_timeout_(uint8_t reg, uint16_t *value);
  void mark_application_lost_();
  void pump_response_();

  bool timed_out_() const { return this->time_reached_(this->deadline_); }

  bool time_reached_(uint32_t deadline) const { return static_cast<int32_t>(millis() - deadline) >= 0; }

  void set_modem_lines_(bool dtr, bool rts);
};

}  // namespace ventilation_unit
}  // namespace esphome
