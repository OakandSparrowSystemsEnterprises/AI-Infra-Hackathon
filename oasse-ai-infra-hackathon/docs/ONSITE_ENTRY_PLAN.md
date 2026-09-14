# Onsite Entry Plan

This is the focused arrival plan for the Intel Physical AI Challenge. The objective is to turn the existing software rehearsal into the onsite hardware proof with the minimum possible integration churn.

## Before leaving

- Event app registration complete.
- T&Cs accepted.
- Profile photo added for badge printing.
- Registration QR code ready offline on the phone.
- Repository credentials confirmed.
- Gatekeeper endpoint/token available locally, never committed.
- Intel sponsor resources and this repo available offline.
- Bring any useful Intel-based development laptop for parallel work, but treat the event kit as the primary hardware target.

Venue: Santa Clara Convention Center, 5001 Great America Parkway, Santa Clara, CA 95054.

Conference registration opens at **7:30 AM**. Target arrival is **7:45-8:00 AM**, before the expected registration peak.

## Door-to-green plan

### 7:45-8:45 — Badge and physical setup

1. Scan the event-app QR code and print badge/lanyard.
2. Go directly to Hackathon Rooms **203/204**.
3. Identify the Intel table/mentor contact and confirm the team is on the **Intel Physical AI Challenge**.
4. Do not switch tracks or chase other sponsor demos while the build path is unverified.

### 9:00 — Hardware distribution begins

As soon as the Intel kit is in hand:

1. Boot the provided machine.
2. Activate `intel_dev_env`.
3. Run Intel's `verify_stack.py`.
4. Record the exact hardware/runtime versions and OpenVINO devices.
5. Pull the exact current `main` commit.
6. Run our non-actuating preflight.
7. Ask the sponsor-binding questions in `ONSITE_SPONSOR_BINDING.md`.
8. Scaffold and fill the local sponsor bridge.
9. Resolve all bindings without motion.

**First-hour success condition:** the Intel stack verifies, camera and robot APIs are identified, the model/planner path is understood, the sponsor bindings resolve, and no authority-core file has been edited.

## Mandatory hackathon information windows

Do not code through information that can change the challenge or submission requirements.

### Tuesday, September 15

- **9:00 AM** — Hackathon Rooms 203/204 open; hardware distribution/coordination begins.
- **10:30 AM** — Opening ceremony.
- **10:45 AM** — Partners' words.
- **11:10 AM** — Project submission workshop and pitching-form explanation.
- **5:00 PM** — Doors close.

Treat the 10:30-11:30 block as required. Capture any challenge-specific object, defect, task, technology, judging, and submission requirements before resuming integration.

### Wednesday, September 16

- **9:00 AM** — Hackathon room opens.
- **10:15 AM** — Day 2 opening words.
- **11:30 AM** — **Submission deadline.**
- **12:30 PM** — Main hackathon room closes.
- **1:00 PM** — Demo showcasing/live pitches in Room 207.
- **5:00 PM** — Doors close.

Do not plan feature work on Wednesday morning. That window is for the final hardware run, evidence freeze, video/deck/repository check, submission, and pitch rehearsal.

### Thursday, September 17

- **1:30-2:00 PM** — Winners ceremony in Expo Theater 2.

Hackathon participants have special conference-content access Thursday. Use that day for Summit sessions and broader networking, not Tuesday morning while the integration path is still uncertain.

## Intel-specific technical lane

Intel's official hackathon resources say the provided stack is built around:

- Intel Core Ultra / Arc / NPU
- Ubuntu 24.04
- Physical AI Studio
- OpenVINO 2026.3
- Anomalib 2.6.0
- LeRobot
- PyTorch XPU
- CPU/GPU/NPU verification

Our build should consume those components through the existing adapter seams rather than replacing them.

Official resource:
https://docs.openedgeplatform.intel.com/dev/edge-ai-suites/robotics-ai-suite/resources/hackathon_resources.html

## Questions to get answered immediately by the Intel engineer

Get these answers before changing code:

1. What exact robot/arm/controller is assigned to us?
2. What is the camera device and capture API?
3. What object(s), defect(s), and physical task define today's challenge?
4. Is there a required Anomalib model/template or are teams expected to train/export their own?
5. What are the expected OpenVINO device(s) for the demo: CPU, GPU, NPU, or any?
6. What output names and thresholds should we use for the provided detector/export?
7. What is the intended Physical AI Studio workflow?
8. What LeRobot/VLA policy invocation should teams use?
9. What coordinate frame, units, trajectory format, and speed limits does the robot controller expect?
10. What exact API call is the final physical send point?
11. Does the controller return a command ID or other correlated acknowledgement?
12. What is the supported stop/cancel/E-stop path for an in-flight command?
13. What sponsor technology must be visibly demonstrated to qualify for the track?
14. Are there mandatory screenshots, logs, measurements, or runtime evidence for judging?
15. At the 11:10 workshop, what exact submission fields, repository visibility, video format/duration, deck format, and demo URL are required?

Write the answers into the onsite evidence notes. Do not rely on memory later.

## Submission requirement check

LabLab's general guide says a complete submission normally includes:

- a working prototype others can use online;
- a video presentation;
- a pitch deck;
- repository access/GitHub as part of the project evidence.

The event-specific **11:10 AM submission workshop is authoritative** if it differs from the general guide. Confirm the following there:

- public repository vs judge-only repository access;
- whether a live public demo URL is required for this physical-hardware track;
- pitch-video duration and upload format;
- slide-deck format/page limits;
- track selection;
- required sponsor technology fields;
- whether onsite judges evaluate live hardware independently of the online submission.

Do not make the private repository public until the event-specific requirement is confirmed.

## No-sidetrack rules

Until the Intel path is green:

- no switching to Qualcomm or SiMa tracks;
- no architecture rewrites;
- no new research layer;
- no broad Summit networking block;
- no optional sponsor integration unrelated to the Intel challenge;
- no reinstalling working sponsor packages simply to match our local pins;
- no demo-polish work before the camera -> detector -> planner -> Gatekeeper -> actuator path works.

If the sponsor changes an API or task, modify the thin bridge first. The core authority layer moves only if the sponsor exposes a genuine contract mismatch.

## Definition of onsite-ready

Before first motion:

- Intel sponsor stack passes its own verifier.
- Our preflight passes.
- Camera/context binding is explicit.
- Detector/model identity and thresholds are explicit.
- Planner output satisfies the strict action contract.
- Robot send point is known and interceptable before send.
- Action acknowledgement behavior is understood.
- Stop/E-stop procedure is understood.
- Live Gatekeeper non-actuating contract probe passes.
- Hardware operator approves the smallest test movement.

Then move the robot.
