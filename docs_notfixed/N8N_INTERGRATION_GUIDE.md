# n8n Integration Guide

Complete guide for integrating n8n workflows with your voice assistant.

## 📋 Table of Contents

1. [Overview](#overview)
2. [Quick Start](#quick-start)
3. [Setup Instructions](#setup-instructions)
4. [Configuration](#configuration)
5. [Testing](#testing)
6. [Available Workflows](#available-workflows)
7. [Creating Custom Workflows](#creating-custom-workflows)
8. [Troubleshooting](#troubleshooting)

---

## 🎯 Overview

The n8n integration allows your voice assistant to trigger external workflows for:

- ✅ **Email** (Gmail, Outlook)
- ✅ **Calendar** (Google Calendar, Outlook)
- ✅ **Notes** (Joplin, Notion, Evernote)
- ✅ **Messaging** (Slack, Discord, Teams)
- ✅ **Task Management** (Todoist, ClickUp, Asana)
- ✅ **GitHub** (Issues, PRs)
- ✅ **Google Sheets** (Logging, tracking)
- ✅ **Home Automation** (Home Assistant)
- ✅ **Custom Workflows**

### Why n8n?

- **Visual Workflow Editor**: Easy to build and modify workflows
- **No Code Required**: Drag-and-drop interface
- **100+ Integrations**: Connect to any service
- **Self-Hosted**: Keep your data private
- **Flexible**: Combine multiple services in one workflow

---

## 🚀 Quick Start

### 1. Install n8n

```bash
# Using npm
npm install -g n8n

# Or using Docker
docker run -it --rm \
  --name n8n \
  -p 5678:5678 \
  -v ~/.n8n:/home/node/.n8n \
  n8nio/n8n
```

### 2. Start n8n

```bash
n8n start
```

Visit: http://localhost:5678

### 3. Configure Environment Variables

Add to your `.env` file:

```bash
# n8n Configuration
N8N_BASE_URL=http://localhost:5678
N8N_AUTH_TOKEN=  # Optional: For authentication

# Test Webhook (REQUIRED FOR TESTING)
N8N_TEST_WEBHOOK=/webhook-test/ac0a62b1-2305-4176-a743-a1c7a96a541a

# Optional: Specific workflow webhooks
N8N_EMAIL_WEBHOOK=/webhook/send-email-abc123
N8N_CALENDAR_WEBHOOK=/webhook/calendar-xyz789
N8N_JOPLIN_WEBHOOK=/webhook/joplin-notes-def456
```

### 4. Enable n8n Action

Update `config/modules/actions.yaml`:

```yaml
productivity:
  n8n:
    enabled: true
    description: "Route commands to n8n workflows"
    config_file: "config/modules/n8n.yaml"
```

---

## 🔧 Setup Instructions

### Step 1: Create a Test Workflow

1. **Open n8n**: http://localhost:5678
2. **Create New Workflow**
3. **Add Webhook Trigger**:
   - Click "Add node" → "Webhook"
   - Set **HTTP Method**: POST
   - Set **Path**: `/webhook-test/ac0a62b1-2305-4176-a743-a1c7a96a541a`
   - Click "Execute Workflow"

4. **Add Response Node**:
   - Add "Respond to Webhook" node
   - Set response body:
   ```json
   {
     "success": true,
     "message": "n8n webhook test successful!",
     "received_data": "={{$json}}"
   }
   ```

5. **Save & Activate** the workflow

### Step 2: Test the Connection

Run your voice assistant:

```bash
python main.py --mode text
```

Test commands:
```
> test n8n
> check webhook
> test n8n connection
```

Expected response: "n8n webhook test successful!"

---

## ⚙️ Configuration

### config/modules/n8n.yaml

```yaml
# n8n Server Settings
server:
  base_url: "http://localhost:5678"
  auth_token: null  # Optional

# Webhook Mappings
webhooks:
  # Test Workflow (REQUIRED)
  test_n8n:
    webhook_path: "/webhook-test/ac0a62b1-2305-4176-a743-a1c7a96a541a"
    description: "Test n8n connection"
    confirmation: false
    intents:
      - "test n8n"
      - "test webhook"
      - "check n8n"
      - "n8n test"
      - "webhook test"
  
  # Joplin Notes
  joplin_note:
    webhook_path: null  # Add your webhook path
    description: "Create note in Joplin"
    confirmation: false
    intents:
      - "take note"
      - "note"
      - "remember"
      - "joplin note"
      - "create note"
  
  # Email
  send_email:
    webhook_path: null
    description: "Send email via Gmail"
    confirmation: true
    intents:
      - "send email"
      - "email"
  
  # Calendar
  add_calendar:
    webhook_path: null
    description: "Add event to calendar"
    confirmation: true
    intents:
      - "add to calendar"
      - "schedule"
      - "create appointment"

# Security
security:
  require_confirmation_for:
    - send_email
    - slack_message
    - github_issue
    - add_calendar
  
  max_requests_per_minute: 10

# Timeout
timeout:
  webhook_timeout_seconds: 30
  retry_attempts: 2
```

### Intent Detection

The n8n action uses **priority matching**:

1. **Test phrases** with "n8n" or "webhook"
2. **Exact intent matches**
3. **Fuzzy matches** with word boundaries
4. **Workflow name** matches

---

## 🧪 Testing

### Test Commands

```bash
# Start in text mode
python main.py --mode text

# Test connection
> test n8n
> check webhook

# Test specific workflows
> joplin note: Buy milk and eggs
> send email to john about meeting
> add to calendar: Meeting tomorrow at 2pm
```

### Debugging

Enable debug logging in `config/settings.yaml`:

```yaml
logging:
  level: "DEBUG"
  log_conversations: true
```

Check logs:
```bash
tail -f logs/assistant.log | grep n8n
```

---

## 📚 Available Workflows

### 1. Test Workflow (Required)

**Purpose**: Verify n8n connection

**Setup**:
- Webhook path: `/webhook-test/ac0a62b1-2305-4176-a743-a1c7a96a541a`
- Response: Simple success message

**Voice Commands**:
- "test n8n"
- "check webhook"
- "n8n test"

---

### 2. Joplin Notes

**Purpose**: Create notes in Joplin

**n8n Workflow**:
1. **Webhook** trigger
2. **Joplin** node: Create note
   - Title: Extract from `user_input`
   - Body: Full `user_input` text
   - Notebook: "Voice Notes"
3. **Respond to Webhook**

**Setup in n8n**:
```
Webhook → Joplin (Create Note) → Respond
```

**Voice Commands**:
- "take note: Meeting tomorrow at 3pm"
- "joplin note: Buy groceries"
- "remember: Call dentist"

**Response Format**:
```json
{
  "success": true,
  "message": "Note created in Joplin",
  "data": {
    "note_id": "abc123",
    "title": "Meeting tomorrow at 3pm"
  }
}
```

---

### 3. Email (Gmail/Outlook)

**Purpose**: Send emails

**n8n Workflow**:
1. **Webhook** trigger
2. **AI Extract** recipient and subject
3. **Gmail/Outlook** node: Send email
4. **Respond to Webhook**

**Voice Commands**:
- "send email to john about meeting"
- "email sarah: Project update"

**Response Format**:
```json
{
  "success": true,
  "message": "Email sent to john@example.com",
  "data": {
    "email_id": "xyz789"
  }
}
```

---

### 4. Calendar Events

**Purpose**: Add events to Google Calendar

**n8n Workflow**:
1. **Webhook** trigger
2. **AI Extract** date, time, title
3. **Google Calendar** node: Create event
4. **Respond to Webhook**

**Voice Commands**:
- "add to calendar: Meeting tomorrow at 2pm"
- "schedule: Dentist appointment Friday 10am"

---

### 5. Task Management

**Purpose**: Create tasks in Todoist/ClickUp/Asana

**n8n Workflow**:
1. **Webhook** trigger
2. **Extract** task details
3. **Todoist/ClickUp** node: Create task
4. **Respond to Webhook**

**Voice Commands**:
- "create task: Review pull request 123"
- "add task: Fix login bug"

---

## 🛠️ Creating Custom Workflows

### Example: Joplin Note Workflow

#### Step 1: Create Workflow in n8n

1. **Add Webhook Node**:
   - HTTP Method: POST
   - Path: `/webhook/joplin-notes`
   - Execute workflow to get URL

2. **Add Joplin Node**:
   - Operation: Create Note
   - Title: `={{$json.user_input}}`
   - Body: `={{$json.user_input}}`
   - Notebook: Select your notebook

3. **Add Respond Node**:
   ```json
   {
     "success": true,
     "message": "Note created: {{$json.title}}",
     "data": {
       "note_id": "={{$json.id}}",
       "title": "={{$json.title}}"
     }
   }
   ```

4. **Save & Activate**

#### Step 2: Add to Configuration

Update `config/modules/n8n.yaml`:

```yaml
webhooks:
  joplin_note:
    webhook_path: "/webhook/joplin-notes"
    description: "Create note in Joplin"
    confirmation: false
    intents:
      - "take note"
      - "joplin note"
      - "remember"
```

#### Step 3: Add to Environment (Optional)

Add to `.env`:
```bash
N8N_JOPLIN_WEBHOOK=/webhook/joplin-notes
```

#### Step 4: Test

```bash
python main.py --mode text

> take note: Buy milk and eggs
# Response: "Note created: Buy milk and eggs"
```

---

## 📊 Response Format

All n8n workflows should return this format:

### Success Response
```json
{
  "success": true,
  "message": "Human-readable message",
  "data": {
    // Optional additional data
  }
}
```

### Error Response
```json
{
  "success": false,
  "error": "Error description",
  "message": "User-friendly error message"
}
```

---

## 🐛 Troubleshooting

### Issue: "No matching n8n workflow found"

**Cause**: Intent not matching correctly

**Solution**:
1. Check `config/modules/n8n.yaml` intents
2. Add more specific intents
3. Enable debug logging to see matching process

```bash
> rag: stats  # Check if n8n action is loaded
```

---

### Issue: "Webhook request timed out"

**Cause**: n8n workflow taking too long

**Solution**:
1. Check n8n workflow is active
2. Increase timeout in config:
```yaml
timeout:
  webhook_timeout_seconds: 60
```

---

### Issue: "Connection refused"

**Cause**: n8n not running

**Solution**:
```bash
# Check if n8n is running
curl http://localhost:5678

# Start n8n
n8n start
```

---

### Issue: Webhook returns 404

**Cause**: Webhook path incorrect

**Solution**:
1. Check webhook URL in n8n workflow
2. Copy exact path from n8n
3. Update `webhook_path` in config

---

## 🔐 Security

### Confirmation Requirements

Some actions require confirmation for security:

```yaml
security:
  require_confirmation_for:
    - send_email
    - slack_message
    - github_issue
```

### Authentication Token

Add authentication to n8n:

1. Generate token in n8n settings
2. Add to `.env`:
```bash
N8N_AUTH_TOKEN=your_token_here
```

---

## 📈 Advanced Features

### Memory Context

n8n workflows receive memory context automatically:

```json
{
  "user_input": "send email to john",
  "context": "User previously mentioned john@example.com",
  "timestamp": "2025-01-15T10:30:00Z"
}
```

Use in workflows with `={{$json.context}}`

### Rate Limiting

Configured in `n8n.yaml`:

```yaml
security:
  max_requests_per_minute: 10
```

### Retry Logic

Automatic retries on failure:

```yaml
timeout:
  retry_attempts: 2
  retry_delay_seconds: 5
```

---

## 📝 Example Workflows

### Complete Joplin Note Workflow

```
Webhook Trigger
  ↓
HTTP Request (Optional: Summarize with AI)
  ↓
Joplin - Create Note
  ↓
Respond to Webhook
```

### Email with AI Processing

```
Webhook Trigger
  ↓
OpenAI - Extract recipient & subject
  ↓
Gmail - Send Email
  ↓
Respond to Webhook
```

---

## 🎯 Best Practices

1. **Test First**: Always create test workflow before production
2. **Use Descriptive Names**: Clear workflow names help debugging
3. **Add Error Handling**: Include error branches in n8n
4. **Set Timeouts**: Don't let workflows run forever
5. **Log Everything**: Enable logging for troubleshooting
6. **Require Confirmation**: For sensitive actions (email, payments)
7. **Use Memory Context**: Leverage conversation history
8. **Keep It Simple**: Start with basic workflows, add complexity later

---

## 📚 Resources

- **n8n Documentation**: https://docs.n8n.io
- **n8n Community**: https://community.n8n.io
- **Joplin API**: https://joplinapp.org/api/references/rest_api/
- **Voice Assistant Docs**: See `docs/` folder

---

## 🆘 Support

Issues? Check:
1. Logs: `logs/assistant.log`
2. n8n Execution History
3. Network: `curl -X POST http://localhost:5678/webhook-test/...`
4. Configuration: `config/modules/n8n.yaml`

---

## 📄 License

Part of Voice Assistant project - MIT License