# django-payments-razorpay

[![PyPI version](https://badge.fury.io/py/django-payments-razorpay.svg)](https://badge.fury.io/py/django-payments-razorpay)

Razorpay payment provider for [django-payments](https://github.com/django-oscar/django-payments), compatible with both traditional Django views and Django REST Framework (DRF).

## Table of Contents

- [Features](#features)
- [Installation](#installation)
- [Requirements](#requirements)
- [Getting Started](#getting-started)
  - [1. Install the Package](#1-install-the-package)
  - [2. Add to Installed Apps](#2-add-to-installed-apps)
  - [3. Configure Payment Variants](#3-configure-payment-variants)
- [Usage with Traditional Django Views](#usage-with-traditional-django-views)
  - [4. Update URLs](#4-update-urls)
  - [5. Create Views](#5-create-views)
  - [6. Create Templates](#6-create-templates)
- [Usage with Django REST Framework](#usage-with-django-rest-framework)
  - [4. Create DRF Views](#4-create-drf-views)
  - [5. Update URLs](#5-update-urls)
  - [6. Update Frontend](#6-update-frontend)
- [Fix for JavaScript Syntax Errors](#fix-for-javascript-syntax-errors)
- [Testing](#testing)
- [Security Considerations](#security-considerations)
- [Additional Notes](#additional-notes)
- [License](#license)

## Features

- Seamless integration with Razorpay payment gateway.
- Compatible with both traditional Django views and Django REST Framework.
- Supports payment initialization, processing, and refunding.
- Handles payment status updates and error management.
- Easy to install and configure.

## Installation

```bash
pip install django-payments-razorpay
```

## Requirements

- Python 3.6+
- Django 2.2+
- django-payments 0.14.0+
- razorpay 1.3.0+
- djangorestframework 3.11.0+ (if using DRF)

## Getting Started

### 1. Install the Package

Install the package using `pip`:

```bash
pip install django-payments-razorpay
```

### 2. Add to Installed Apps

Add `'payments'` and `'payments_razorpay'` to your `INSTALLED_APPS` in `settings.py`:

```python
INSTALLED_APPS = [
    # ...
    'payments',
    'payments_razorpay',
    # ...
]
```

### 3. Configure Payment Variants

Add the Razorpay provider to your `PAYMENT_VARIANTS` in `settings.py`:

```python
PAYMENT_VARIANTS = {
    'razorpay': ('payments_razorpay.RazorpayProvider', {
        'public_key': 'your_razorpay_public_key',   # Replace with your Razorpay public key
        'secret_key': 'your_razorpay_secret_key',   # Replace with your Razorpay secret key
    }),
}
```

Replace `'your_razorpay_public_key'` and `'your_razorpay_secret_key'` with the API keys provided by Razorpay. You can obtain these keys from the Razorpay Dashboard under **Settings** > **API Keys**.

## Usage with Traditional Django Views

### 4. Update URLs

Add the necessary URLs to handle the payment process. In your `urls.py`:

```python
from django.urls import path
from payments import views as payment_views
from your_app.views import start_payment

urlpatterns = [
    # ...
    path('payment/<int:payment_id>/', payment_views.payment_details, name='payment_details'),
    path('payment/<int:payment_id>/process/', payment_views.process_payment, name='process_payment'),
    path('payment/<int:payment_id>/done/', payment_views.payment_successful, name='payment_successful'),
    path('payment/<int:payment_id>/failed/', payment_views.payment_failed, name='payment_failed'),
    path('start-payment/<int:order_id>/', start_payment, name='start_payment'),
    # ...
]
```

### 5. Create Views

Create views to handle the payment initiation and processing.

#### a. Start Payment View

```python
# your_app/views.py

from django.shortcuts import get_object_or_404, redirect
from payments import get_payment_model
from your_app.models import Order  # Replace with your actual Order model

def start_payment(request, order_id):
    order = get_object_or_404(Order, id=order_id)
    Payment = get_payment_model()
    payment = Payment.objects.create(
        variant='razorpay',  # This is the variant from PAYMENT_VARIANTS
        description='Payment for Order {}'.format(order_id),
        total=order.total,  # Assuming order.total is a Decimal
        currency='INR',
        billing_first_name=order.billing_first_name,
        billing_last_name=order.billing_last_name,
        billing_email=order.billing_email,
        billing_phone=order.billing_phone,
        customer_ip_address=request.META.get('REMOTE_ADDR'),
    )
    return redirect('payment_details', payment_id=payment.id)
```

#### b. Payment Details View

The `payment_details` view is provided by `django-payments`. Ensure it's included in your URLs as shown above.

### 6. Create Templates

#### a. Payment Template

Create a template at `templates/payment.html` with the following content:

```html
{% extends "base.html" %}

{% block content %}
  <h1>Make a Payment</h1>
  <form method="post">
    {% csrf_token %}
    {{ form }}
    <button type="submit">Proceed to Payment</button>
  </form>
{% endblock %}
```

#### b. Razorpay Template

The package includes a Razorpay-specific template at `payments/razorpay.html`, which is used by the provider.

**Note:** If you encounter JavaScript syntax errors related to the `"notes"` field in the template, see the [Fix for JavaScript Syntax Errors](#fix-for-javascript-syntax-errors) section below.

## Usage with Django REST Framework

### 4. Create DRF Views

#### a. Install Django REST Framework

If not already installed, install DRF:

```bash
pip install djangorestframework
```

Add `'rest_framework'` to your `INSTALLED_APPS`:

```python
INSTALLED_APPS = [
    # ...
    'rest_framework',
    # ...
]
```

#### b. Create API Views

Create DRF API views to handle payment initialization and processing.

```python
# your_app/views.py

from rest_framework.views import APIView
from rest_framework.response import Response
from rest_framework import status
from payments import get_payment_model, PaymentError
from payments import RedirectNeeded

Payment = get_payment_model()

class RazorpayPaymentInitView(APIView):
    """
    API View to initialize Razorpay payment.
    """

    def post(self, request):
        # Extract necessary data from the request
        order_data = request.data

        # Create a new Payment object
        payment = Payment.objects.create(
            variant='razorpay',
            description='Payment for Order {}'.format(order_data.get('order_id')),
            total=order_data.get('amount'),  # Ensure this is a Decimal
            currency='INR',
            billing_first_name=order_data.get('first_name', ''),
            billing_last_name=order_data.get('last_name', ''),
            billing_email=order_data.get('email', ''),
            billing_phone=order_data.get('phone', ''),
            customer_ip_address=request.META.get('REMOTE_ADDR'),
        )

        try:
            form = payment.get_form(data=None)
        except RedirectNeeded as redirect_to:
            # Handle redirect if necessary
            return Response({'redirect_url': str(redirect_to)}, status=status.HTTP_302_FOUND)

        # Return the initial data required for Razorpay Checkout
        return Response({
            'payment_id': payment.id,
            'razorpay_options': form.initial
        }, status=status.HTTP_200_OK)


class RazorpayPaymentProcessView(APIView):
    """
    API View to process Razorpay payment confirmation.
    """

    def post(self, request, payment_id):
        payment = Payment.objects.get(id=payment_id)
        provider = payment.get_provider()

        try:
            provider.process_data(payment, request)
        except PaymentError as e:
            return Response({'detail': str(e)}, status=status.HTTP_400_BAD_REQUEST)

        # Return the payment status
        return Response({'status': payment.status}, status=status.HTTP_200_OK)
```

### 5. Update URLs

Add the API endpoints to your `urls.py`:

```python
from django.urls import path
from your_app.views import RazorpayPaymentInitView, RazorpayPaymentProcessView

urlpatterns = [
    # ...
    path('api/payment/razorpay/init/', RazorpayPaymentInitView.as_view(), name='razorpay_payment_init'),
    path('api/payment/razorpay/process/<int:payment_id>/', RazorpayPaymentProcessView.as_view(), name='razorpay_payment_process'),
    # ...
]
```

### 6. Update Frontend

In your frontend application (e.g., React, Angular, Vue.js), handle the payment process as follows:

#### a. Initialize Payment

Make a POST request to `/api/payment/razorpay/init/` with the order details:

```javascript
fetch('/api/payment/razorpay/init/', {
    method: 'POST',
    headers: {
        'Content-Type': 'application/json',
        // Include authentication headers if necessary
    },
    body: JSON.stringify({
        order_id: 'ORDER123',
        amount: 1000.00,  // Amount in INR
        first_name: 'John',
        last_name: 'Doe',
        email: 'john.doe@example.com',
        phone: '+919876543210'
    })
})
.then(response => response.json())
.then(data => {
    var options = data.razorpay_options;
    options.handler = function (response) {
        // Send the payment confirmation to the server
        fetch(`/api/payment/razorpay/process/${data.payment_id}/`, {
            method: 'POST',
            headers: {
                'Content-Type': 'application/json',
                // Include authentication headers if necessary
            },
            body: JSON.stringify(response)
        })
        .then(processResponse => processResponse.json())
        .then(processData => {
            if (processData.status === 'confirmed') {
                // Payment successful
                alert('Payment successful!');
            } else {
                // Handle other statuses
                alert('Payment status: ' + processData.status);
            }
        })
        .catch(error => {
            console.error('Error processing payment:', error);
            alert('Error processing payment.');
        });
    };

    // Initialize Razorpay
    var rzp1 = new Razorpay(options);
    rzp1.open();
})
.catch(error => {
    console.error('Error initializing payment:', error);
    alert('Error initializing payment.');
});
```

#### b. Handle Payment Success

In the `handler` function of the Razorpay options, send the payment details back to the server for processing.

### 7. Frontend Integration Notes

- **Include Razorpay Script:** Ensure you include the Razorpay Checkout script in your HTML or load it dynamically.

  ```html
  <script src="https://checkout.razorpay.com/v1/checkout.js"></script>
  ```

- **CSRF Protection:** Since DRF's `APIView` does not enforce CSRF checks, you don't need to handle CSRF tokens unless you're mixing session-based authentication.
- **Authentication:** If your API requires authentication, ensure that your frontend includes the necessary tokens or credentials in the headers.
- **Error Handling:** Update your frontend to handle different response statuses and display appropriate messages to the user.

## Fix for JavaScript Syntax Errors

If you encounter JavaScript syntax errors in the `razorpay.html` template, specifically related to the `"notes"` field, you need to ensure that the `notes` dictionary is properly serialized into JSON.

### Problem Explanation

The error occurs because the `notes` field is rendered as a Python dictionary, which is not valid JavaScript syntax.

### Solution

#### Step 1: Modify the Provider's `get_form` Method

In `payments_razorpay/razorpay_provider.py`, import the `json` module and serialize the `notes` dictionary:

```python
import json

class RazorpayProvider(BasicProvider):
    # ... existing code ...

    def get_form(self, payment, data=None):
        # ... existing code ...

        notes = {
            'email': payment.billing_email or '',
            'phone': payment.billing_phone or '',
        }

        # Serialize the notes dictionary to a JSON-formatted string
        notes_json = json.dumps(notes)

        # Update the initial data
        initial = {
            # ... existing fields ...
            'notes': notes_json,
            # ... existing fields ...
        }

        # ... existing code ...
```

#### Step 2: Update the Template

In `payments_razorpay/templates/payments/razorpay.html`, ensure the `notes` field is rendered correctly:

```html
<script>
    var options = {
        // ... existing fields ...
        "notes": {{ form.initial.notes|safe }},
        // ... existing fields ...
    };
    // ... existing code ...
</script>
```

By properly serializing the `notes` dictionary into JSON and rendering it safely into your JavaScript code, you resolve the syntax errors.

## Testing

Before deploying to production, thoroughly test the payment flow:

- Use Razorpay's test keys.
- Test successful payments, failures, and edge cases.
- Ensure that all statuses (`PaymentStatus.CONFIRMED`, `PaymentStatus.ERROR`, etc.) are handled correctly.
- Verify that payments are correctly recorded in your database.

## Security Considerations

- **API Keys:** Never expose your Razorpay secret key in client-side code. Keep it secure on the server.
- **Data Validation:** Always validate and sanitize input data from the client.
- **HTTPS:** Ensure your site is served over HTTPS to secure communication between the client and server.
- **Signature Verification:** The package handles signature verification, but ensure you do not skip this step when processing payments.
- **Logging:** Be cautious with logging sensitive information. Avoid logging full credit card numbers, CVV, or personal user data.

## Additional Notes

- **Refunds:** The `refund` method is implemented in the provider. You can call `payment.refund()` to process refunds.
- **Auto-Capture:** The provider is set to auto-capture payments. If you need manual capture, adjust the `payment_capture` parameter.
- **Customizations:** Feel free to customize the payment form and frontend as per your application's requirements.
- **Support:** For any issues or questions, please open an issue on the [GitHub repository](https://github.com/hyndex/django-payments-razorpay).

## License

[MIT License](LICENSE)

---

# Requirements.txt

Include a `requirements.txt` file in your project to specify the dependencies:

```text
Django>=2.2
django-payments>=0.14.0
razorpay>=1.3.0
djangorestframework>=3.11.0  # If using DRF
```

---

## Final Notes

By following this guide, you can integrate Razorpay payments into your Django application using `django-payments-razorpay`, whether you're using traditional Django views or Django REST Framework. Remember to replace placeholder values like API keys with your actual credentials and customize the code as needed for your application.

Feel free to contribute to the package by submitting pull requests or opening issues on GitHub.

---

**GitHub Repository:** [hyndex/django-payments-razorpay](https://github.com/hyndex/django-payments-razorpay)

**PyPI Package:** [django-payments-razorpay](https://pypi.org/project/django-payments-razorpay/)