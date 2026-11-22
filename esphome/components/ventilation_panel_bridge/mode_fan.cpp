#include "ventilation_panel_bridge.h"

#include "esphome/core/log.h"

#include <algorithm>
#include <cstring>

namespace esphome {
namespace ventilation_panel_bridge {

ESPHOME_LOG_TAG(TAG, "ventilation_panel_bridge.fan");

void VentilationPanelBridgeModeFan::dump_config() { LOG_FAN("", "Ventilation mode", this); }

optional<uint8_t> VentilationPanelBridgeModeFan::restored_mode() {
  auto restore = this->restore_state_();
  if (!restore.has_value())
    return {};
  if (!restore->state)
    return 0;
  return static_cast<uint8_t>(std::clamp(restore->speed, 1, 3));
}

void VentilationPanelBridgeModeFan::publish_mode(uint8_t mode) {
  this->state = mode != 0;
  // Keep the last speed/preset while standby/off so the UI restores it on the next turn-on.
  if (mode != 0) {
    this->speed = mode;
    auto traits = this->get_traits();
    const auto &presets = traits.supported_preset_modes();
    if (static_cast<size_t>(mode - 1) < presets.size())
      this->set_preset_mode_(presets[mode - 1]);
  }
  this->publish_state();
}

void VentilationPanelBridgeModeFan::control(const fan::FanCall &call) {
  if (this->parent_ == nullptr)
    return;
  bool on = this->state;
  int speed = this->speed;
  if (call.get_state().has_value())
    on = *call.get_state();
  if (call.get_speed().has_value())
    speed = *call.get_speed();
  // A preset selects one of the ordered speeds (presets alias speeds 1-3 in declared order).
  if (call.has_preset_mode()) {
    auto traits = this->get_traits();
    const auto &presets = traits.supported_preset_modes();
    for (size_t i = 0; i < presets.size(); i++) {
      if (std::strcmp(presets[i], call.get_preset_mode()) == 0) {
        speed = static_cast<int>(i) + 1;
        on = true;
        break;
      }
    }
  }
  // Turning on without an explicit speed defaults to the lowest speed.
  if (on && speed < 1)
    speed = 1;
  uint8_t mode = on ? static_cast<uint8_t>(speed) : 0;
  if (mode > 3)
    mode = 3;
  this->parent_->set_mode_override(mode);
}

}  // namespace ventilation_panel_bridge
}  // namespace esphome
