# n8n Response Standard

**All n8n workflows MUST return a standardized JSON response.**

## 📋 Why This Matters

When your webhook doesn't return anything, the voice assistant gets:
- ❌ "Unknown error" 
- ❌ No confirmation
- ❌ Unclear if it worked

With a standard response:
- ✅ Clear success/failure
- ✅ User-friendly messages
- ✅ Optional data for debugging

---

## 📐 Response Format

### Success Response
```json
{
  "success": true,
  "message": "Human-readable confirmation message",
  "data": {
    // Optional: Additional data
  }
}
```

### Error Response
```json
{
  "success": false,
  "message": "User-friendly error message",
  "error": "Technical error details (optional)"
}
```

---

## 🔧 Implementation Guide

### Every Workflow MUST End With "Respond to Webhook"

#### Step 1: Add "Respond to Webhook" Node

In **every** n8n workflow, as the **last node**:

1. Click the `+` after your last action node
2. Search for **"Respond to Webhook"**
3. Add it to your workflow

#### Step 2: Configure Response

##### For Success:
```json
{
  "success": true,
  "message": "Your confirmation message here",
  "data": {
    "id": "={{$json.id}}",
    "other_field": "={{$json.other_field}}"
  }
}
```

##### For Error Handling:
Add an **Error Trigger** node:
```json
{
  "success": false,
  "message": "Something went wrong",
  "error": "={{$json.error.message}}"
}
```

---

## 📝 Examples by Workflow Type

### 1. Test Workflow

**Workflow**: Webhook → Respond

**Response**:
```json
{
  "success": true,
  "message": "n8n webhook test successful!",
  "data": {
    "received_input": "={{$json.user_input}}",
    "workflow_name": "={{$json.workflow_name}}",
    "timestamp": "={{$json.timestamp}}"
  }
}
```

**Voice Response**: "n8n webhook test successful!"

---

### 2. Joplin Notes

**Workflow**: Webhook → Joplin (Create Note) → Respond

**Success Response**:
```json
{
  "success": true,
  "message": "Note created: {{$json.title}}",
  "data": {
    "note_id": "={{$json.id}}",
    "title": "={{$json.title}}",
    "notebook": "={{$json.parent_id}}"
  }
}
```

**Error Response** (if Joplin fails):
```json
{
  "success": false,
  "message": "Failed to create note in Joplin",
  "error": "={{$json.error.message}}"
}
```

**Voice Responses**:
- Success: "Note created: Buy milk and eggs"
- Error: "Failed to create note in Joplin"

---

### 3. Email (Gmail/Outlook)

**Workflow**: Webhook → OpenAI (Extract) → Gmail (Send) → Respond

**Success Response**:
```json
{
  "success": true,
  "message": "Email sent to {{$('OpenAI').json.recipient}}",
  "data": {
    "recipient": "={{$('OpenAI').json.recipient}}",
    "subject": "={{$('OpenAI').json.subject}}",
    "message_id": "={{$json.id}}"
  }
}
```

**Error Response**:
```json
{
  "success": false,
  "message": "Failed to send email",
  "error": "Invalid recipient email address"
}
```

**Voice Responses**:
- Success: "Email sent to john@example.com"
- Error: "Failed to send email"

---

### 4. Calendar Event

**Workflow**: Webhook → OpenAI (Parse date) → Google Calendar → Respond

**Success Response**:
```json
{
  "success": true,
  "message": "Event added: {{$json.summary}} on {{$json.start.dateTime}}",
  "data": {
    "event_id": "={{$json.id}}",
    "summary": "={{$json.summary}}",
    "start": "={{$json.start.dateTime}}",
    "calendar": "primary"
  }
}
```

**Voice Response**: "Event added: Team meeting on 2025-11-08T14:00:00"

---

### 5. Slack Message

**Workflow**: Webhook → Slack (Post) → Respond

**Success Response**:
```json
{
  "success": true,
  "message": "Message sent to Slack #{{$json.channel}}",
  "data": {
    "channel": "={{$json.channel}}",
    "timestamp": "={{$json.ts}}"
  }
}
```

---

### 6. GitHub Issue

**Workflow**: Webhook → OpenAI (Extract) → GitHub (Create Issue) → Respond

**Success Response**:
```json
{
  "success": true,
  "message": "GitHub issue #{{$json.number}} created",
  "data": {
    "issue_number": "={{$json.number}}",
    "title": "={{$json.title}}",
    "url": "={{$json.html_url}}"
  }
}
```

---

### 7. Task Management (Todoist/ClickUp)

**Workflow**: Webhook → Todoist (Create Task) → Respond

**Success Response**:
```json
{
  "success": true,
  "message": "Task created: {{$json.content}}",
  "data": {
    "task_id": "={{$json.id}}",
    "content": "={{$json.content}}",
    "project": "={{$json.project_id}}"
  }
}
```

---

### 8. Google Sheets Logging

**Workflow**: Webhook → Google Sheets (Append) → Respond

**Success Response**:
```json
{
  "success": true,
  "message": "Data logged to spreadsheet",
  "data": {
    "sheet": "={{$json.sheet_name}}",
    "row": "={{$json.row_number}}"
  }
}
```

---

## 🛡️ Error Handling Best Practices

### Add Error Trigger to Every Workflow

1. **Add "Error Trigger" node** parallel to your main flow
2. **Connect to "Respond to Webhook"**
3. **Configure error response**:

```json
{
  "success": false,
  "message": "Workflow failed: {{$json.error.message}}",
  "error": {
    "type": "={{$json.error.name}}",
    "message": "={{$json.error.message}}",
    "node": "={{$json.error.node.name}}"
  }
}
```

### Workflow Structure:
```
Webhook → Action Node → Respond (success)
           ↓
      Error Trigger → Respond (failure)
```

---

## 🎯 Quick Template

Copy this for every new workflow:

### Basic Template
```
1. Webhook (Trigger)
2. [Your Action Nodes]
3. Respond to Webhook (Success)
4. Error Trigger → Respond to Webhook (Failure)
```

### Success Response Template
```json
{
  "success": true,
  "message": "Action completed: [description]",
  "data": {
    "id": "={{$json.id}}",
    "name": "={{$json.name}}"
  }
}
```

### Error Response Template
```json
{
  "success": false,
  "message": "Action failed: [reason]",
  "error": "={{$json.error.message}}"
}
```

---

## ✅ Validation Checklist

Before activating any workflow, verify:

- [ ] Has "Respond to Webhook" as last node
- [ ] Response includes `success` field (true/false)
- [ ] Response includes `message` field (human-readable)
- [ ] Has Error Trigger with failure response
- [ ] Tested with sample data
- [ ] Response appears in voice assistant correctly

---

## 🧪 Testing Response Format

### Test in n8n

1. Execute workflow manually
2. Check "Output" tab of Respond node
3. Verify JSON structure matches standard

### Test from Voice Assistant

```bash
python main.py --mode text

> test n8n
# Should see: "n8n webhook test successful!"

> take note: Test note
# Should see: "Note created: Test note"
```

### Test with curl

```bash
curl -X POST http://localhost:5678/webhook-test/your-webhook-id \
  -H "Content-Type: application/json" \
  -d '{"user_input":"test"}' \
  | jq
```

Expected output:
```json
{
  "success": true,
  "message": "n8n webhook test successful!",
  "data": {...}
}
```

---

## 🐛 Common Issues

### Issue: "Unknown error"

**Cause**: No "Respond to Webhook" node

**Fix**: Add "Respond to Webhook" as last node

---

### Issue: Response not showing

**Cause**: Incorrect JSON format

**Fix**: Ensure response has `success` and `message` fields

---

### Issue: Empty message

**Cause**: Using `{{$json.field}}` that doesn't exist

**Fix**: Check field names in previous node's output

---

## 📊 Response Data Guidelines

### What to Include in `data`

**Good** (useful info):
```json
{
  "data": {
    "id": "123",
    "name": "Document",
    "url": "https://..."
  }
}
```

**Bad** (too much):
```json
{
  "data": {
    "entire_response": "={{}}"  // Don't include everything
  }
}
```

### Keep It Simple

Only include:
- IDs for reference
- URLs for links
- Key fields user might need
- Confirmation details

---

## 🎓 Learning Path

1. **Start**: Test workflow with basic response
2. **Practice**: Add responses to existing workflows
3. **Master**: Include error handling
4. **Optimize**: Add useful data fields
5. **Perfect**: Consistent format across all workflows

---

## 📚 Related Documentation

- **N8N_SETUP_GUIDE.md**: Complete workflow creation guide
- **N8N_INTEGRATION.md**: Quick start guide
- **TESTING_N8N.md**: Testing procedures

---

## ✨ Benefits of Standard Responses

✅ **User Experience**: Clear confirmation messages
✅ **Debugging**: Easy to identify failures
✅ **Consistency**: Same format everywhere
✅ **Extensibility**: Easy to add new workflows
✅ **Monitoring**: Track success/failure rates

---

**Remember**: Every workflow = Webhook + Action + **Respond to Webhook**

No response = "Unknown error" ❌
Standard response = Happy user ✅