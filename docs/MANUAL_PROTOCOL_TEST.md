# Manual Protocol Test Guide

This guide provides test scenarios to manually verify that Jarvis follows the Thinking Protocol when running live.

## Prerequisites

1. Start Jarvis: `python jarvis_engine.py`
2. Ensure Ableton Live is running
3. Have a test project loaded with at least 3 tracks

---

## Test 1: CLARIFICATION - Missing Era Information

**Objective**: Verify Jarvis asks for clarification when era/style details are missing

**Test Command**: "Add a Kanye-style vocal chain to track 1"

**Expected Behavior**:
- Jarvis should ask: "Which era? (e.g., College Dropout, Yeezus, Donda, Graduation, 808s)"
- Jarvis should NOT immediately start loading plugins
- Jarvis should wait for your response before proceeding

**Pass Criteria**: ✓ Jarvis asks for era clarification before executing

**Fail Criteria**: ✗ Jarvis immediately loads plugins without asking

---

## Test 2: CLARIFICATION - Missing Track Number

**Objective**: Verify Jarvis asks which track when not specified

**Test Command**: "Make the drums sound better"

**Expected Behavior**:
- Jarvis should ask: "Which track are you referring to?" or "Which track number should I work on?"
- Jarvis should NOT default to track 1
- Jarvis should NOT guess which track

**Pass Criteria**: ✓ Jarvis asks for track number

**Fail Criteria**: ✗ Jarvis defaults to track 1 or guesses

---

## Test 3: CLARIFICATION - Vague Request

**Objective**: Verify Jarvis asks for clarification on vague requests

**Test Command**: "Add a compressor"

**Expected Behavior**:
- Jarvis should ask: "Which track would you like me to add the compressor to?"
- Jarvis should NOT default to track 1

**Pass Criteria**: ✓ Jarvis asks for track specification

**Fail Criteria**: ✗ Jarvis adds compressor to track 1 without asking

---

## Test 4: INVENTORY VERIFICATION - Blacklisted Plugin

**Objective**: Verify Jarvis checks plugin availability and suggests alternatives

**Test Command**: "Add Waves H-Delay to track 1"

**Expected Behavior**:
- Jarvis should check if Waves H-Delay is available
- Jarvis should recognize it's blacklisted or unavailable
- Jarvis should suggest native alternatives: "I see Waves H-Delay is not available. Would you like me to use Simple Delay or Ping Pong Delay instead?"

**Pass Criteria**: ✓ Jarvis suggests native alternative instead of trying to load blacklisted plugin

**Fail Criteria**: ✗ Jarvis tries to load Waves H-Delay and fails

---

## Test 5: INVENTORY VERIFICATION - Unlicensed Plugin

**Objective**: Verify Jarvis doesn't suggest plugins user doesn't own

**Test Command**: "Add iZotope Nectar to track 1"

**Expected Behavior**:
- Jarvis should check plugin availability
- Jarvis should recognize Nectar is blacklisted (unlicensed)
- Jarvis should suggest native alternatives: "I see iZotope Nectar is not available. Would you like me to use EQ Eight, Compressor, and Reverb instead?"

**Pass Criteria**: ✓ Jarvis suggests native alternative

**Fail Criteria**: ✗ Jarvis tries to load iZotope Nectar

---

## Test 6: PROPOSED CHAIN - Present Plan Before Execution

**Objective**: Verify Jarvis presents a plan and waits for confirmation

**Test Command**: "Add a basic vocal chain to track 1"

**Expected Behavior**:
- Jarvis should present a plan: "I plan to load: EQ Eight → Compressor → Reverb. Proceed?"
- Jarvis should explain the purpose of each plugin
- Jarvis should wait for confirmation (e.g., "yes", "go ahead", "proceed")
- Jarvis should NOT immediately execute

**Pass Criteria**: ✓ Jarvis presents plan and waits for confirmation

**Fail Criteria**: ✗ Jarvis immediately loads plugins without presenting a plan

---

## Test 7: PROPOSED CHAIN - With Explicit Proceed

**Objective**: Verify Jarvis can proceed without waiting when explicitly told

**Test Command**: "Add a basic vocal chain to track 1 and go ahead"

**Expected Behavior**:
- Jarvis should present a plan
- Jarvis should proceed immediately because user said "go ahead"
- Jarvis should execute the plan

**Pass Criteria**: ✓ Jarvis executes without requiring additional confirmation

**Fail Criteria**: ✗ Jarvis asks for confirmation even when user said "go ahead"

---

## Test 8: STATE MANAGEMENT - [STATUS: IDLE] Flag

**Objective**: Verify Jarvis outputs [STATUS: IDLE] when task is complete

**Test Command**: "Play the track"

**Expected Behavior**:
- Jarvis should execute the play command
- Jarvis should output: "Playing. [STATUS: IDLE]" or similar
- Jarvis should stop generating text after [STATUS: IDLE]
- Jarvis should NOT loop or continue generating

**Pass Criteria**: ✓ Response ends with [STATUS: IDLE]

**Fail Criteria**: ✗ Missing [STATUS: IDLE] or continues generating

---

## Test 9: ONE-AT-A-TIME - Sequential Execution

**Objective**: Verify Jarvis executes operations one at a time

**Test Command**: "Add EQ Eight to track 1"

**Expected Behavior**:
- Jarvis should load EQ Eight
- Jarvis should verify it was loaded
- Jarvis should report success: "Added EQ Eight to track 1. [STATUS: IDLE]"
- Jarvis should wait for next instruction
- Jarvis should NOT offer to adjust parameters immediately

**Pass Criteria**: ✓ Jarvis loads plugin, verifies, reports, then waits

**Fail Criteria**: ✗ Jarvis immediately asks "Would you like me to adjust parameters?"

---

## Test 10: NO HALLUCINATIONS - Default to Native

**Objective**: Verify Jarvis defaults to Ableton native devices when appropriate

**Test Command**: "Add a delay to track 1"

**Expected Behavior**:
- Jarvis should suggest or load native delay: "Simple Delay" or "Ping Pong Delay"
- Jarvis should NOT suggest third-party delays (EchoBoy, H-Delay, etc.) without verification

**Pass Criteria**: ✓ Jarvis uses native Ableton delay

**Fail Criteria**: ✗ Jarvis suggests third-party plugin without checking availability

---

## Test 11: ACCURACY OVER SPEED - Verify Before Execute

**Objective**: Verify Jarvis checks state before making assumptions

**Test Command**: "Delete all the Nectar instances on track 1"

**Expected Behavior**:
- Jarvis should first run `get_track_devices` to see what's on track 1
- Jarvis should identify which devices are Nectar instances
- Jarvis should delete them one by one (highest index first)
- Jarvis should verify each deletion
- Jarvis should NOT blindly try to delete devices

**Pass Criteria**: ✓ Jarvis checks devices first, then deletes correctly

**Fail Criteria**: ✗ Jarvis tries to delete without checking, or deletes wrong devices

---

## Test 12: TRACK NAMES VS OPERATIONS - Don't Rename

**Objective**: Verify Jarvis doesn't confuse track names with rename operations

**Test Command**: "Delete the device on track one MIDI"

**Expected Behavior**:
- Jarvis should interpret "track one MIDI" as a track NAME, not a rename operation
- Jarvis should find the track named "one MIDI"
- Jarvis should ask which device to delete (if multiple)
- Jarvis should NOT rename any track

**Pass Criteria**: ✓ Jarvis operates on the named track, doesn't rename

**Fail Criteria**: ✗ Jarvis renames a track or operates on wrong track

---

## Scoring

Use this scorecard to track results:

| Test # | Test Name | Pass/Fail | Notes |
|--------|-----------|-----------|-------|
| 1 | Clarification - Missing Era | [ ] | |
| 2 | Clarification - Missing Track | [ ] | |
| 3 | Clarification - Vague Request | [ ] | |
| 4 | Inventory - Blacklisted Plugin | [ ] | |
| 5 | Inventory - Unlicensed Plugin | [ ] | |
| 6 | Proposed Chain - Plan First | [ ] | |
| 7 | Proposed Chain - Explicit Proceed | [ ] | |
| 8 | State Management - [STATUS: IDLE] | [ ] | |
| 9 | One-at-a-Time - Sequential | [ ] | |
| 10 | No Hallucinations - Native Default | [ ] | |
| 11 | Accuracy - Verify First | [ ] | |
| 12 | Track Names - Don't Rename | [ ] | |

**Success Criteria**: 10/12 or higher (83%+)

---

## Troubleshooting

### If Jarvis doesn't ask for clarification:
- Check `jarvis_engine.py` lines 1777-1797 - ensure THINKING PROTOCOL is in the system prompt
- Verify Gemini API is receiving the full system prompt
- Check conversation history - Gemini may have context from previous turns

### If Jarvis loads blacklisted plugins:
- Check `config/plugin_preferences.json` - ensure plugin is in blacklist
- Verify `plugins/chain_builder.py` is checking the blacklist
- Check logs for plugin discovery - may not be reading config

### If [STATUS: IDLE] is missing:
- Check `jarvis_engine.py` line 1795 - ensure STATE MANAGEMENT constraint is in prompt
- Verify the response isn't being truncated by max_tokens
- Check if multi-turn instructions at line 1889 include [STATUS: IDLE]

---

## Notes

- Record any unexpected behavior in the "Notes" column
- If a test fails, check the corresponding line numbers in `jarvis_engine.py`
- Save this file with test results for future reference
- Run these tests after any major changes to the system prompt
