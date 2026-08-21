---
name: google-calendar-union-leave
description: Query and summarize union business leave records from Google Calendar using Chinese keywords such as "會務公假" and "會務". Use when the user asks for leave usage statistics by year, month, explicit date range, or employee name, especially tables with name, applied hours, reasons, and totals.
---

# Google Calendar Union Leave

## Overview

Use this skill to build repeatable Google Calendar summaries for union business leave events. The default search keywords are `會務公假` and `會務`.

## Calendar Defaults

- Use Google Calendar connector tools.
- Default calendar ID: `99d56c9e32b7a9e5daa6095e18c6b0281f3e4ccaab93951b8ba6335027f5f33c@group.calendar.google.com`.
- Default timezone: `Asia/Taipei`.
- Default query keywords: `會務公假`, `會務`.
- If the user gives another calendar ID, use it for that request.

## Date Handling

- Convert user date language into explicit `time_min` and `time_max`.
- For "YYYY 年 M 月截至目前", use the first day of that month at `00:00:00+08:00` through the current date at `23:59:59+08:00`.
- For a full month, use the first day at `00:00:00+08:00` through the last day at `23:59:59+08:00`.
- For a date range, use the given start date at `00:00:00+08:00` and end date at `23:59:59+08:00`.
- State the resolved period in the answer.

## Query Workflow

1. Search the target calendar with query `會務公假` and the resolved bounded time window.
2. Search the same target calendar and bounded time window with query `會務`.
3. Merge results from both searches and deduplicate by event `id`.
4. Keep events whose `summary`, `display_title`, or description indicates union business leave. Prefer exact `會務公假` matches; include broader `會務` matches when the event context is still leave-related or requested by the user.
5. If the user specifies a name, filter returned events by exact name in `summary`, `display_title`, or description fields such as `員工` or `員工姓名`.
6. If keyword searches return no events, say so and do not infer from unrelated leave types.
7. If results appear incomplete, run an unfiltered bounded search for the same calendar and keep only events whose title or description contains `會務公假` or `會務`.
8. Base calculations only on returned calendar evidence.

## Hour Calculation

- For timed events, calculate elapsed hours from `start` to `end`, including cross-midnight events.
- For all-day events, calculate business leave hours as `8 hours * number of calendar days`.
- If the description explicitly says `1日`, treat it as 8 hours even when the visible calendar duration is 08:00-17:00.
- If both an explicit period and calendar start/end exist, prefer the explicit period when it is more specific.
- Mention the calculation rule briefly in the final answer.

## Output

- Use a Markdown table by default.
- Include at least: `姓名`, `目前已申請時數`, `事由等資訊`.
- Group by person and sum hours across all matching events.
- Combine reasons with semicolons; remove repeated boilerplate such as `奉理事長指派` only when doing so improves readability and does not change meaning.
- Include a total hours line after the table.
- If the user asks for a single name, include only that person plus the total for that person.
