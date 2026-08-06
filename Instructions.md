# Take-Home Instructions

## Goal

Turn the existing prompt router into a useful chat experience. The backend already accepts a prompt and returns the model it recommends in the `selected_model` field. Your job is to build the front end and work out how that routing decision can be used with the Claude and ChatGPT websites.

Please use the existing classifier rather than replacing it. You can change the backend if needed to support your implementation.

## Tasks

### 1. Build a chat front end

Create a simple, usable chat interface where someone can enter and submit a prompt. Include the basic states you would expect in a real product, such as loading and error feedback. The design does not need to be elaborate, but the main flow should be easy to understand.

### 2. Connect the front end to the router

Send each submitted prompt to `POST /v1/route` and use the returned `selected_model` value. Show the routing decision clearly in the interface so we can see exactly which model the router selected and whether the selection mode was `scored` or `random`.

Keep the integration clean enough that the routing result could be handed to a model provider or another delivery layer. Document any mapping, fallback, or compatibility decisions you make.

### 3. Connect the router to Claude and ChatGPT

Explore and implement a way for the classifier to work when a user is writing a prompt on [claude.ai](https://claude.ai) or [chatgpt.com](https://chatgpt.com). The goal is to capture the prompt, classify it, and route or hand it off to the recommended model with as little manual work as possible.

You may use a browser extension, userscript, local companion service, or another approach you think is appropriate. We know the two sites expose different models and have technical limitations. Handle those constraints thoughtfully, make the best working prototype you can, and explain what would be needed to make it production-ready.

## Deliverables

Please plan for the following on **Saturday, August 8, 2026**:

- Send me your updated repository before our conversation, including all code and documentation needed to run your work.
- Include a short README update that explains your setup, architecture, and any unfinished pieces.
- If you incur API, token, or other project costs, track the amount and purpose of each expense and send me the receipts. You are not expected to spend money unnecessarily.
- Be ready for a **20-minute conversation** where you demonstrate what you built, explain your technical choices, and discuss what you would do next.

Do not commit API keys, session data, or other secrets to the repository. Use environment variables and include an example environment file if credentials are needed.

## Evaluation criteria

We will evaluate:

1. How well you completed the assigned tasks and how reliably the result works.
2. How clearly you explain and demonstrate your work during our conversation.
3. Any thoughtful features or improvements you built beyond the core tasks.

It is completely okay if you do not finish all three tasks. One task done really well is better than all three done superficially. Make as much progress as you can, and be ready to explain your priorities, tradeoffs, and remaining work.
