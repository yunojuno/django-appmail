Django-AppMail
--------------

Django app for managing transactional email templates

This project arose out of a project to integrate a large transactional Django application with Mandrill, and the lessons learned. It also owes a minor h/t to this project from 2011 (https://github.com/hugorodgerbrown/AppMail).

The core requirement is to provide an easy way to add / edit email templates (HTML and TXT) to a Django project, in such a way that it doesn't require a developer to make changes. The easiest way to use templated emails in Django is to rely on the in-built template structure, but that means that the templates are held in files, under version control, which makes it very hard for non-developers to edit.

1. Use Django model for each email
2. Simple custom admin form for editing HTML and TXT templates
3. Support standard Django template variables
4. Expose super-simple functions for sending
5. Fire on_sent signal so that external apps can hook in to the event

.. code:: python

    from appmail import send
  
    def send_order_confirmation(order_id):
        """Send the order confirmation email to the recipient.""" 
        order = Orders.objects.get(id=order_id)
        payload = {
            "greeting": "Hi, %s" % order.recipient,
            "line_items": order.line_items
        }
        # send(recipient, template, template_context)
        send(order.recipient, 'order_confirmation', payload)
