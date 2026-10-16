from app import db, helpers

TEMPLATES = {
    "ticket_created": "We got your request #{ticket_id}: {subject}",
    "comment_added": "New reply on #{ticket_id} at {when}",
    "credit_issued": "A credit of ${amount} was applied to your account for #{ticket_id}",
}


def notify(customer, template, **context):
    message = {
        "to": customer["email"],
        "template": template,
        "body": TEMPLATES[template].format(**context),
        "queued_at": helpers.now(),
    }
    db.DB["outbox"].append(message)
    return message
