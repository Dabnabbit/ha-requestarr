---
status: complete
phase: 05-library-state-card-polish-validation
source: [05-01-SUMMARY.md, 05-02-SUMMARY.md]
started: 2026-02-28T03:55:00Z
updated: 2026-02-28T03:58:00Z
---

## Current Test

[testing complete]

## Tests

### 1. In Library Badge on Movie/TV Results
expected: Search for a movie or TV show already in your Radarr/Sonarr library. A green "In Library" pill badge appears overlaid at the bottom of the poster thumbnail.
result: skipped
reason: Integration not deployed to HA instance yet

### 2. In Library Badge on Music Results
expected: Search for a music artist already in your Lidarr library. A green "In Library" pill badge appears overlaid on the circular avatar thumbnail.
result: skipped
reason: Integration not deployed to HA instance yet

### 3. Disabled Button for In-Library Items
expected: For any search result that is in the library, the Request button is replaced by a grayed-out disabled button labeled "In Library". It cannot be clicked.
result: skipped
reason: Integration not deployed to HA instance yet

### 4. Request Button for Non-Library Items
expected: For search results NOT in the library, the normal Request button still appears and is clickable (confirming in-library detection doesn't break normal request flow).
result: skipped
reason: Integration not deployed to HA instance yet

### 5. Card Editor Opens in Lovelace
expected: Edit the Requestarr card in Lovelace UI. A visual editor appears with a title text input field and service toggle checkboxes.
result: skipped
reason: Integration not deployed to HA instance yet

### 6. Card Editor Shows Only Configured Services
expected: The card editor only shows toggle checkboxes for services that are actually configured (e.g., if Lidarr is not set up, no Lidarr toggle appears).
result: skipped
reason: Integration not deployed to HA instance yet

### 7. Card Editor Saves Config
expected: Change a setting in the card editor (e.g., toggle a service off or change the title). Save the card. Reload the page — the change persists.
result: skipped
reason: Integration not deployed to HA instance yet

### 8. All Tests Pass
expected: Run `python3 -m pytest tests/ -q` from the project root. All 18 tests pass with no failures or errors.
result: pass

### 9. README Documentation
expected: Open README.md. It documents: installation via HACS, config flow setup for Radarr/Sonarr/Lidarr, card usage with all three media types, and card editor options.
result: pass

## Summary

total: 9
passed: 2
issues: 0
pending: 0
skipped: 7

## Gaps

[none yet]
