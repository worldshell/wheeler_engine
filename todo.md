# WorldShell Implementation TODO

- [ ] Core Logic
    - [ ] **World Loader**: Load `world_definition.yaml` into Python objects.
    - [ ] **Player Class**: Manage AP, location, inventory, and awake/sleep state.
    - [ ] **Game Engine**:
        - [ ] Turn management (Day/Night phases).
        - [ ] Action processing (`move`, `take`, `examine`, `sleep`, `lock`, `unlock`).
        - [ ] **Trace System**: Generate traces based on actions.
        - [ ] **Observation Filter**: The "Cat Box" logic (what can H see vs Z see).
    - [ ] **CLI Interface**: Simple text-based loop for 2 players.

- [ ] Content
    - [ ] Refine `world_definition.yaml` if needed during implementation.

- [ ] Testing
    - [ ] Playtest the "Observation Filter" logic (ensure H doesn't see Z's hidden actions).
    - [ ] Playtest the "Noise/Wake-up" logic.
