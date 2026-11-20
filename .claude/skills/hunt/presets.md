# Presets

A preset names a queue of platforms that `/hunt` runs one after another, in the
order given: `/hunt daily`, `/hunt daily devops apply`.

- A preset holds platforms only. The track (`swe` / `devops` / `both`) and `apply` come
  from the invocation and apply to every platform in the queue.
- Presets and platforms can be mixed: `/hunt daily,djinni`. Repeats are dropped.
- A name must not clash with a platform (a file in `platforms/`), an alias (`li`, `te`,
  `ij`, `arc`, `genie`, `djini`, `parks`, `companies`, `remote`, `sk`, `gl`) or a flag (`swe`,
  `devops`, `both`, `apply`, `unattended`, `selected-*`).

| Preset | Platforms, in order | What for |
|---|---|---|
| `daily` | djinni, linkedin, infojobs, tecnoempleo | The everyday run: Djinni plus the Spanish boards. |
| `spain` | linkedin, infojobs, tecnoempleo | All Spanish boards that support apply. |
| `remote-wide` | djinni, arcdev, remote-boards, globallogic | Remote roles outside the Spanish market. |
