"""
VNPay Payment Gateway Service
Handles VNPay payment integration for restaurant management system
"""

import hashlib
import hmac
import urllib.parse
import uuid
from decimal import Decimal
from datetime import datetime
from typing import Dict, Optional, Tuple
import logging

from django.conf import settings
from django.utils import timezone
from rest_framework.exceptions import ValidationError

logger = logging.getLogger(__name__)


class VNPayService:
    """
    VNPay Payment Gateway Service

    Handles:
    - Payment URL generation
    - Payment callback verification
    - Signature creation and validation
    - Payment status management
    """

    def __init__(self):
        self.api_url = settings.VNPAY_API_URL
        self.payment_url = settings.VNPAY_PAYMENT_URL
        self.tmn_code = settings.VNPAY_TMN_CODE
        self.hash_secret = settings.VNPAY_HASH_SECRET_KEY
        self.version = settings.VNPAY_VERSION
        self.command = settings.VNPAY_COMMAND
        self.return_url = settings.VNPAY_RETURN_URL
        self.callback_url = settings.VNPAY_CALLBACK_URL
        self.currency = settings.VNPAY_CURRENCY_CODE
        self.locale = settings.VNPAY_LOCALE
        self.order_type = settings.VNPAY_ORDER_TYPE

    def generate_payment_url(
        self,
        order_id: str,
        amount: Decimal,
        order_info: str,
        client_ip: str,
        bank_code: Optional[str] = None
    ) -> Tuple[str, str]:
        """
        Generate VNPay payment URL

        Args:
            order_id: Order ID (must be unique)
            amount: Payment amount in VND
            order_info: Order description
            client_ip: Client IP address
            bank_code: Optional bank code for bank selection

        Returns:
            Tuple of (payment_url, transaction_reference)

        Raises:
            ValidationError: If parameters are invalid
        """
        try:
            # Generate unique transaction reference
            transaction_ref = f"{order_id}_{int(timezone.now().timestamp())}"

            # Prepare payment data
            payment_data = {
                'vnp_Version': self.version,
                'vnp_Command': self.command,
                'vnp_TmnCode': self.tmn_code,
                'vnp_Amount': str(int(amount * 100)),  # VNPay requires amount * 100
                'vnp_CurrCode': self.currency,
                'vnp_TxnRef': transaction_ref,
                'vnp_OrderInfo': order_info,
                'vnp_OrderType': self.order_type,
                'vnp_Locale': self.locale,
                'vnp_ReturnUrl': self.return_url,
                'vnp_IpAddr': client_ip,
                'vnp_CreateDate': timezone.now().strftime('%Y%m%d%H%M%S'),
            }

            # Add optional bank code if provided
            if bank_code:
                payment_data['vnp_BankCode'] = bank_code

            # Generate secure hash
            secure_hash = self._generate_signature(payment_data)
            payment_data['vnp_SecureHash'] = secure_hash
            payment_data['vnp_SecureHashType'] = 'HMACSHA512'

            # Build payment URL
            query_string = '&'.join([
                f"{key}={urllib.parse.quote_plus(str(value))}"
                for key, value in sorted(payment_data.items())
            ])

            payment_url = f"{self.payment_url}?{query_string}"

            logger.info(f"Generated VNPay payment URL for order {order_id}, amount {amount}")
            return payment_url, transaction_ref

        except Exception as e:
            logger.error(f"Error generating VNPay payment URL: {str(e)}")
            raise ValidationError(f"Failed to generate payment URL: {str(e)}")

    def verify_callback(self, callback_data: Dict) -> Tuple[bool, Optional[Dict]]:
        """
        Verify VNPay callback data

        Args:
            callback_data: Dictionary containing VNPay callback parameters

        Returns:
            Tuple of (is_valid, processed_data)
            - is_valid: True if signature is valid (regardless of payment success/fail)
            - processed_data: Dict with payment info including response_code

        Raises:
            ValidationError: If callback data is invalid
        """
        try:
            # Extract callback parameters
            vnp_txn_ref = callback_data.get('vnp_TxnRef')
            vnp_response_code = callback_data.get('vnp_ResponseCode')
            vnp_transaction_no = callback_data.get('vnp_TransactionNo')
            vnp_secure_hash = callback_data.get('vnp_SecureHash')
            vnp_secure_hash_type = callback_data.get('vnp_SecureHashType')

            logger.info(f"Verifying VNPay callback - TxnRef: {vnp_txn_ref}, ResponseCode: {vnp_response_code}")
            logger.info(f"Received SecureHash: {vnp_secure_hash[:20]}... (truncated)")

            if not all([vnp_txn_ref, vnp_response_code]):
                logger.error("Missing required VNPay callback parameters")
                raise ValidationError("Missing required VNPay callback parameters")

            # Create a copy of data for verification (excluding hash and hash type)
            verify_data = {
                key: value for key, value in callback_data.items()
                if key.startswith('vnp_') and key not in ['vnp_SecureHash', 'vnp_SecureHashType']
            }

            logger.info(f"Verify data keys: {list(verify_data.keys())}")

            # Verify signature if provided
            if vnp_secure_hash:
                expected_hash = self._generate_signature(verify_data)
                logger.info(f"Expected SecureHash: {expected_hash[:20]}... (truncated)")
                
                is_signature_valid = self._verify_signature(vnp_secure_hash, expected_hash)
                logger.info(f"Signature validation result: {is_signature_valid}")
                
                if not is_signature_valid:
                    logger.warning(f"⚠️ Invalid VNPay signature for transaction {vnp_txn_ref}")
                    # ⚠️ IMPORTANT: Still return the data but mark as invalid
                    return False, None
            else:
                logger.warning("⚠️ No SecureHash provided in callback (test mode?)")

            # Process callback data
            processed_data = {
                'transaction_ref': vnp_txn_ref,
                'response_code': vnp_response_code,
                'transaction_no': vnp_transaction_no or '',
                'amount': Decimal(callback_data.get('vnp_Amount', '0')) / 100,  # Convert back from *100
                'order_info': callback_data.get('vnp_OrderInfo', ''),
                'pay_date': self._parse_vnpay_date(callback_data.get('vnp_PayDate')),
                'bank_code': callback_data.get('vnp_BankCode', ''),
                'card_type': callback_data.get('vnp_CardType', ''),
            }

            logger.info(f"✅ VNPay callback verified successfully - TxnRef: {vnp_txn_ref}, ResponseCode: {vnp_response_code}")
            
            # Return TRUE for valid signature, processed_data contains response_code for success check
            return True, processed_data

        except Exception as e:
            logger.error(f"❌ Error processing VNPay callback: {str(e)}", exc_info=True)
            raise ValidationError(f"Failed to process callback: {str(e)}")

    def query_transaction(self, transaction_ref: str) -> Optional[Dict]:
        """
        Query transaction status from VNPay

        Args:
            transaction_ref: Transaction reference to query

        Returns:
            Dictionary with transaction data or None if failed
        """
        try:
            query_data = {
                'vnp_Version': self.version,
                'vnp_Command': 'querydr',
                'vnp_TmnCode': self.tmn_code,
                'vnp_TxnRef': transaction_ref,
                'vnp_OrderInfo': f'Query transaction {transaction_ref}',
                'vnp_CreateDate': timezone.now().strftime('%Y%m%d%H%M%S'),
            }

            # Generate signature for query
            secure_hash = self._generate_signature(query_data)
            query_data['vnp_SecureHash'] = secure_hash
            query_data['vnp_SecureHashType'] = 'HMACSHA512'

            # Make API request to VNPay
            import requests
            response = requests.post(
                self.api_url,
                data=query_data,
                timeout=settings.VNPAY_TIMEOUT
            )

            if response.status_code == 200:
                result = self._parse_vnpay_response(response.text)
                return result

            logger.warning(f"VNPay query failed for {transaction_ref}: HTTP {response.status_code}")
            return None

        except Exception as e:
            logger.error(f"Error querying VNPay transaction {transaction_ref}: {str(e)}")
            return None

    def _generate_signature(self, data: Dict) -> str:
        """
        Generate HMAC-SHA512 signature for VNPay

        Args:
            data: Dictionary of data to sign

        Returns:
            Hexadecimal signature string
        """
        # Sort data by key
        sorted_data = sorted(data.items())

        # Create query string
        query_string = '&'.join([
            f"{key}={urllib.parse.quote_plus(str(value))}"
            for key, value in sorted_data
        ])

        # Generate HMAC-SHA512 signature
        signature = hmac.new(
            self.hash_secret.encode('utf-8'),
            query_string.encode('utf-8'),
            hashlib.sha512
        ).hexdigest()

        return signature

    def _verify_signature(self, received_signature: str, expected_signature: str) -> bool:
        """
        Verify HMAC signature

        Args:
            received_signature: Signature received from VNPay
            expected_signature: Expected signature calculated locally

        Returns:
            True if signatures match
        """
        return received_signature == expected_signature

    def _parse_vnpay_date(self, date_str: Optional[str]) -> Optional[datetime]:
        """
        Parse VNPay date string to datetime

        Args:
            date_str: Date string in VNPay format (YYYYMMDDHHMMSS)

        Returns:
            Datetime object or None if parsing fails
        """
        if not date_str:
            return None

        try:
            return datetime.strptime(date_str, '%Y%m%d%H%M%S')
        except ValueError:
            logger.warning(f"Invalid VNPay date format: {date_str}")
            return None

    def _parse_vnpay_response(self, response_text: str) -> Dict:
        """
        Parse VNPay API response

        Args:
            response_text: Raw response text from VNPay API

        Returns:
            Dictionary with parsed response data
        """
        response_data = {}

        # Parse URL-encoded response
        for pair in response_text.split('&'):
            if '=' in pair:
                key, value = pair.split('=', 1)
                response_data[key] = urllib.parse.unquote_plus(value)

        return response_data

    def get_error_message(self, response_code: str) -> str:
        """
        Get human-readable error message from VNPay response code

        Args:
            response_code: VNPay response code

        Returns:
            Error message in Vietnamese
        """
        error_codes = {
            '00': 'Giao dịch thành công',
            '01': 'Giao dịch chưa hoàn tất',
            '02': 'Giao dịch bị lỗi',
            '03': 'Reversed Transaction',
            '04': 'Giao dịch đã tồn tại',
            '05': 'Giao dịch không tồn tại',
            '06': 'Mãmerchant không tồn tại',
            '07': 'Giao dịch không thành công do:Tài khoản không đủ tiền',
            '08': 'Giao dịch không thành công do:Lỗi định dạng',
            '09': 'Giao dịch không thành công do:Trùng yêu cầu',
            '10': 'Giao dịch không thành công do:Không xác định được',
            '11': 'Giao dịch không thành công do:Mã kiểm tra không hợp lệ',
            '12': 'Giao dịch không thành công do:Địa chỉ IP không được phép',
            '13': 'Giao dịch không thành công do:Thời gian hết hạn giao dịch',
            '24': 'Giao dịch không thành công do:Khách hàng hủy giao dịch',
            '51': 'Giao dịch không thành công do:Tài khoản không đủ tiền',
            '65': 'Giao dịch không thành công do:Tài khoản chưa được kích hoạt',
            '75': 'Giao dịch không thành công do:Quá số tiền cho phép',
            '79': 'Giao dịch không thành công do:Khách hàng nhập sai mật khẩu quá số lần quy định',
            '99': 'Các lỗi khác'
        }

        return error_codes.get(response_code, 'Mã lỗi không xác định')


# Singleton instance for reuse
vnpay_service = VNPayService()