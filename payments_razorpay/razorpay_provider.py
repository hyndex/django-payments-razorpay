# payments_razorpay/razorpay_provider.py

import json
import razorpay
from django import forms
from django.utils.translation import gettext_lazy as _
from payments import PaymentStatus, PaymentError
from payments.core import BasicProvider
from payments.forms import PaymentForm as BasePaymentForm

class RazorpayPaymentForm(BasePaymentForm):
    razorpay_payment_id = forms.CharField(widget=forms.HiddenInput)
    razorpay_order_id = forms.CharField(widget=forms.HiddenInput)
    razorpay_signature = forms.CharField(widget=forms.HiddenInput)

class RazorpayProvider(BasicProvider):
    """
    Razorpay payment provider for django-payments.
    """

    def __init__(self, public_key, secret_key, **kwargs):
        self.public_key = public_key
        self.secret_key = secret_key
        self.client = razorpay.Client(auth=(self.public_key, self.secret_key))
        super().__init__(**kwargs)

    def get_form(self, payment, data=None):
        """
        Returns a form to be rendered in the payment page.
        Creates a Razorpay order and includes necessary data for the frontend.
        """
        order_amount = int(payment.total * 100)  # Convert to paise
        order_currency = payment.currency
        order_receipt = str(payment.id)
        notes = {
            'email': payment.billing_email or '',
            'phone': payment.billing_phone or '',
        }

        try:
            razorpay_order = self.client.order.create({
                'amount': order_amount,
                'currency': order_currency,
                'receipt': order_receipt,
                'notes': notes,
                'payment_capture': 1  # Auto-capture
            })
        except Exception as e:
            payment.change_status(PaymentStatus.ERROR, str(e))
            raise PaymentError(f"Error creating Razorpay order: {e}")

        # Save the order id in payment
        payment.attrs.razorpay_order_id = razorpay_order['id']
        payment.save()

        # Serialize notes to JSON
        notes_json = json.dumps(notes)

        initial = {
            'razorpay_order_id': razorpay_order['id'],
            'razorpay_key_id': self.public_key,
            'amount': order_amount,
            'currency': order_currency,
            'name': f"{payment.billing_first_name} {payment.billing_last_name}".strip(),
            'description': f'Payment for Order {order_receipt}',
            'image': '',  # Optional: URL to your logo
            'prefill': {
                'name': f"{payment.billing_first_name} {payment.billing_last_name}".strip(),
                'email': payment.billing_email or '',
                'contact': payment.billing_phone or '',
            },
            'notes': notes_json,  # Use the serialized JSON string
            'theme': {
                'color': '#F37254'  # Customize the color
            }
        }

        form = RazorpayPaymentForm(data=data, initial=initial, payment=payment, provider=self)
        return form

    def get_template(self):
        return 'payments/razorpay.html'

    def process_data(self, payment, request):
        """
        Process the data returned from Razorpay after payment.
        Handles both form data and JSON data for DRF compatibility.
        """
        # Handle JSON data for DRF compatibility
        if request.content_type == 'application/json':
            data = request.data
        else:
            data = request.POST or request.GET

        razorpay_order_id = data.get('razorpay_order_id')
        razorpay_payment_id = data.get('razorpay_payment_id')
        razorpay_signature = data.get('razorpay_signature')

        if not all([razorpay_order_id, razorpay_payment_id, razorpay_signature]):
            payment.change_status(PaymentStatus.REJECTED, 'Missing payment details')
            raise PaymentError('Missing payment details')

        params_dict = {
            'razorpay_order_id': razorpay_order_id,
            'razorpay_payment_id': razorpay_payment_id,
            'razorpay_signature': razorpay_signature
        }

        try:
            self.client.utility.verify_payment_signature(params_dict)
        except razorpay.errors.SignatureVerificationError:
            payment.change_status(PaymentStatus.ERROR, 'Signature verification failed')
            raise PaymentError('Signature verification failed')

        # Payment successful
        payment.transaction_id = razorpay_payment_id
        payment.captured_amount = payment.total
        payment.change_status(PaymentStatus.CONFIRMED)
        payment.save()

    def capture(self, payment, amount=None):
        """
        Capture payment if not auto-captured.
        """
        pass  # Not needed as payment_capture is set to '1' for auto-capture

    def refund(self, payment, amount=None):
        """
        Refund the payment.
        """
        if amount is None:
            amount = payment.captured_amount or payment.total
        amount_in_paise = int(amount * 100)
        try:
            self.client.payment.refund(payment.transaction_id, amount_in_paise)
            payment.change_status(PaymentStatus.REFUNDED)
            payment.save()
        except Exception as e:
            payment.change_status(PaymentStatus.ERROR, str(e))
            raise PaymentError(f"Error processing refund: {e}")
