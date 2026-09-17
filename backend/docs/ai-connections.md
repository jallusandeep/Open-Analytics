# AI Connections

Admin Connections stores named OpenAI and Gemini API connections. Enter a connection name, provider, and API key; available models load automatically through the backend for selection. Editing can retain the encrypted saved key. The table stores multiple connections and supports testing access. Default selection is not exposed in Connections; consuming tabs choose the connection they use.

Connections contains no prompts, instructions, token limits, timeout settings, or query interface. Instructions and queries belong in the consuming application tab.

Keys are encrypted with CONNECTION_ENCRYPTION_KEY (ENCRYPTION_KEY alias supported), or a persistent .ai-credentials.key beside the database. Back up this key with the database. Keys are never returned to the browser or placed in provider request URLs.

Admin-only API: GET/POST /api/v1/connections/ai, POST /models for model discovery, PUT/DELETE /{connection_id}, POST /{connection_id}/default and /{connection_id}/test. Discovery supports saved credentials and Gemini pagination; Gemini models are limited to generateContent support.

Provider references: https://developers.openai.com/api/reference/resources/models/methods/list and https://ai.google.dev/api/models
