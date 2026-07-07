# Vulndrone lab

A local ground control lab for a simulated drone fleet, built for practicing web and api
security. Three services run together, a flight simulator underneath, a companion api sitting
in front of it, and a web console on top.

This is not a walkthrough. The lab has multiple privilege tiers and more than one path to
escalate between them. Read the client carefully, not just the parts wired up to visible
buttons.

## What is running

- sitl, ArduCopter SITL built from source, the simulated flight controller
- companion-api, a FastAPI service between SITL and the browser
- dashboard, the web console

## Running it

```
unzip vulndrone.zip
cd vulndrone
docker compose up --build
```

First run takes a while, sitl compiles ArduCopter from source. Later runs are quick.

- Dashboard, http://localhost:3000
- Companion api, http://localhost:8000

## Getting started

The dashboard opens on a sign in screen. There is no self registration, and no full set of
working credentials is handed to you directly. The console does show some operational context
on that screen worth reading closely, and once inside, pay attention to what the console loads
and what it does not show you directly.

Some functionality in this lab is intentionally restricted to a higher privilege tier than the
one you start with. Figuring out how that tier is reached is most of the exercise.

One of the integrations on the dashboard has a reputation among the ops team for behaving a
little unpredictably. Worth paying closer attention to than the others.

## Reporting issues

If something feels broken rather than intentionally vulnerable, for example a crash instead of
a proper response, that is a bug in the lab itself rather than part of the challenge, open an
issue.
