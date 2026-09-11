# Build Clock Guard

Do not hard-code the hackathon implementation unlock to a guessed clock time.

Organizer artifacts currently expose differing agenda details. The repository therefore uses a manual `EVENT_BUILD_OPEN` guard. Leave it at `0` during preparation. Set it to `1` only when the organizer explicitly announces that hacking/building has begun.

The guard is evidence hygiene, not a security boundary. Git history and normal commit timestamps remain the authoritative record of event-created work.
