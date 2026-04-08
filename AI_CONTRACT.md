# TIMEASE — AI Contract

This document specifies the AI layer behavior. Implementation in `timease/api/ai_chat.py`.

> **Status**: Stub. Full specification to be added in Phase E of the implementation.

## Overview

TIMEASE uses OpenAI GPT-4o for conversational school setup. The AI helps users describe their school configuration in natural language, then calls structured tools to save the data.

## Key Principles

- **Single turn**: `MAX_TURNS = 1`. No agentic chaining within a request.
- **Tool-first**: When the user provides data, call the appropriate `save_*` tool immediately.
- **Backend validation**: All data is validated server-side before staging.
- **French UI**: All user-facing messages in French.

## Tool List

_(To be documented in Phase E)_

## SSE Events

_(To be documented in Phase E)_

## System Prompt

_(To be documented in Phase E)_
