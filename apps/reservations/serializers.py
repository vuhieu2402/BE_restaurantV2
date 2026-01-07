"""
Serializers for Reservations app
"""
from rest_framework import serializers
from decimal import Decimal
from .models import Reservation, FIXED_DEPOSIT_AMOUNT


class ReservationSerializer(serializers.ModelSerializer):
    """
    Serializer đầy đủ cho Reservation - hiển thị tất cả thông tin
    """
    customer_info = serializers.SerializerMethodField()
    restaurant_info = serializers.SerializerMethodField()
    table_info = serializers.SerializerMethodField()
    status_display = serializers.CharField(source='get_status_display', read_only=True)
    special_occasion_display = serializers.CharField(source='get_special_occasion_display', read_only=True)
    payment_status = serializers.SerializerMethodField()
    payment_status_display = serializers.SerializerMethodField()
    is_paid = serializers.SerializerMethodField()
    deposit_remaining = serializers.SerializerMethodField()

    # Display fields
    deposit_required_display = serializers.SerializerMethodField()
    deposit_paid_display = serializers.SerializerMethodField()

    class Meta:
        model = Reservation
        fields = [
            'id',
            'reservation_number',
            'customer',
            'customer_info',
            'restaurant',
            'restaurant_info',
            'table',
            'table_info',
            'reservation_date',
            'reservation_time',
            'number_of_guests',
            'status',
            'status_display',
            'contact_name',
            'contact_phone',
            'contact_email',
            'special_requests',
            'notes',
            'deposit_required',
            'deposit_required_display',
            'deposit_paid',
            'deposit_paid_display',
            'deposit_remaining',
            'payment_status',
            'payment_status_display',
            'is_paid',
            'special_occasion',
            'special_occasion_display',
            'checked_in_at',
            'completed_at',
            'created_at',
            'updated_at',
        ]
        read_only_fields = [
            'id', 'reservation_number', 'deposit_required', 'deposit_paid',
            'created_at', 'updated_at', 'checked_in_at', 'completed_at'
        ]

    def get_customer_info(self, obj):
        """Lấy thông tin khách hàng"""
        if obj.customer:
            return {
                'id': obj.customer.id,
                'username': obj.customer.username,
                'full_name': obj.customer.get_full_name(),
                'email': obj.customer.email,
                'phone': obj.customer.phone_number if hasattr(obj.customer, 'phone_number') else None,
            }
        return None

    def get_restaurant_info(self, obj):
        """Lấy thông tin nhà hàng"""
        if obj.restaurant:
            return {
                'id': obj.restaurant.id,
                'name': obj.restaurant.name,
                'slug': obj.restaurant.slug,
                'phone': obj.restaurant.phone_number,
                'address': obj.restaurant.address,
            }
        return None

    def get_table_info(self, obj):
        """Lấy thông tin bàn"""
        if obj.table:
            return {
                'id': obj.table.id,
                'table_number': obj.table.table_number,
                'floor': obj.table.floor,
                'capacity': obj.table.capacity,
            }
        return None

    def get_payment_status(self, obj):
        """Lấy trạng thái thanh toán"""
        return obj.payment_status

    def get_payment_status_display(self, obj):
        """Hiển thị trạng thái thanh toán"""
        return obj.get_payment_status_display()

    def get_is_paid(self, obj):
        """Kiểm tra đã thanh toán chưa"""
        return obj.is_paid

    def get_deposit_remaining(self, obj):
        """Số tiền cọc còn cần thanh toán"""
        return float(obj.deposit_remaining)

    def get_deposit_required_display(self, obj):
        """Format hiển thị deposit_required"""
        return f"{obj.deposit_required:,.0f}đ"

    def get_deposit_paid_display(self, obj):
        """Format hiển thị deposit_paid"""
        return f"{obj.deposit_paid:,.0f}đ"


class ReservationListSerializer(serializers.ModelSerializer):
    """
    Lightweight serializer cho list view - chỉ hiển thị thông tin cơ bản
    """
    restaurant_name = serializers.CharField(source='restaurant.name', read_only=True)
    status_display = serializers.CharField(source='get_status_display', read_only=True)
    payment_status_display = serializers.SerializerMethodField()
    is_paid = serializers.SerializerMethodField()
    deposit_required_display = serializers.SerializerMethodField()

    class Meta:
        model = Reservation
        fields = [
            'id',
            'reservation_number',
            'restaurant_name',
            'reservation_date',
            'reservation_time',
            'number_of_guests',
            'status',
            'status_display',
            'contact_name',
            'contact_phone',
            'deposit_required',
            'deposit_required_display',
            'payment_status_display',
            'is_paid',
            'created_at',
        ]

    def get_payment_status_display(self, obj):
        """Hiển thị trạng thái thanh toán"""
        return obj.get_payment_status_display()

    def get_is_paid(self, obj):
        """Kiểm tra đã thanh toán chưa"""
        return obj.is_paid

    def get_deposit_required_display(self, obj):
        """Format hiển thị deposit_required"""
        return f"{obj.deposit_required:,.0f}đ"


class ReservationCreateSerializer(serializers.Serializer):
    """
    Serializer cho việc tạo reservation
    Validate tất cả input và business rules
    """
    restaurant_id = serializers.IntegerField(required=True, help_text="ID nhà hàng")
    table_id = serializers.IntegerField(
        required=False,
        allow_null=True,
        help_text="ID bàn (optional - nhà hàng sẽ gán sau)"
    )
    reservation_date = serializers.DateField(required=True, help_text="Ngày đặt (YYYY-MM-DD)")
    reservation_time = serializers.TimeField(required=True, help_text="Giờ đặt (HH:MM)")
    number_of_guests = serializers.IntegerField(
        required=True,
        min_value=1,
        help_text="Số lượng khách"
    )
    contact_name = serializers.CharField(
        required=True,
        max_length=200,
        help_text="Tên người đặt"
    )
    contact_phone = serializers.CharField(
        required=True,
        max_length=20,
        help_text="Số điện thoại"
    )
    contact_email = serializers.EmailField(
        required=False,
        allow_null=True,
        help_text="Email"
    )
    special_requests = serializers.CharField(
        required=False,
        allow_blank=True,
        allow_null=True,
        help_text="Yêu cầu đặc biệt"
    )
    special_occasion = serializers.ChoiceField(
        choices=Reservation.OCCASION_CHOICES,
        required=False,
        allow_null=True,
        help_text="Dịp đặc biệt"
    )


    def validate_restaurant_id(self, value):
        """Validate restaurant exists và đang hoạt động"""
        from apps.restaurants.models import Restaurant

        try:
            restaurant = Restaurant.objects.get(id=value, is_active=True)
            return value
        except Restaurant.DoesNotExist:
            raise serializers.ValidationError("Nhà hàng không tồn tại hoặc không hoạt động.")

    def validate_table_id(self, value):
        """Validate table exists và available"""
        if value:
            from apps.restaurants.models import Table

            try:
                table = Table.objects.get(id=value, is_active=True)
                if table.status not in ['available', 'reserved']:
                    raise serializers.ValidationError("Bàn không khả dụng.")
                return value
            except Table.DoesNotExist:
                raise serializers.ValidationError("Bàn không tồn tại.")
        return value

    def validate(self, attrs):
        """Validate toàn bộ dữ liệu"""
        from apps.restaurants.models import Restaurant, Table
        from django.utils import timezone
        from datetime import datetime, timedelta

        restaurant_id = attrs.get('restaurant_id')
        table_id = attrs.get('table_id')
        reservation_date = attrs.get('reservation_date')
        reservation_time = attrs.get('reservation_time')
        number_of_guests = attrs.get('number_of_guests')

        # Validate table thuộc restaurant
        if table_id and restaurant_id:
            try:
                table = Table.objects.get(id=table_id)
                if table.restaurant_id != restaurant_id:
                    raise serializers.ValidationError({
                        'table_id': 'Bàn không thuộc nhà hàng đã chọn.'
                    })
            except Table.DoesNotExist:
                pass

        # Validate reservation_datetime không phải quá khứ
        if reservation_date and reservation_time:
            reservation_datetime = timezone.make_aware(
                datetime.combine(reservation_date, reservation_time)
            )
            now = timezone.now()

            # Không thể đặt bàn cho thời điểm trong quá khứ
            if reservation_datetime < now:
                raise serializers.ValidationError({
                    'reservation_datetime': 'Không thể đặt bàn cho thời điểm trong quá khứ.'
                })

            # Tối thiểu 1 tiếng trước khi đặt
            min_reservation_time = now + timedelta(hours=1)
            if reservation_datetime < min_reservation_time:
                raise serializers.ValidationError({
                    'reservation_datetime': 'Vui lòng đặt trước ít nhất 1 giờ.'
                })

        # Validate số khách với bàn (nếu có chọn bàn)
        if table_id and number_of_guests:
            try:
                table = Table.objects.get(id=table_id)
                if number_of_guests > table.capacity:
                    raise serializers.ValidationError({
                        'number_of_guests': f'Số khách vượt quá sức chứa của bàn ({table.capacity} khách).'
                    })
            except Table.DoesNotExist:
                pass

        return attrs


class ReservationUpdateStatusSerializer(serializers.Serializer):
    """
    Serializer cho việc cập nhật trạng thái reservation
    """
    status = serializers.ChoiceField(
        choices=Reservation.STATUS_CHOICES,
        required=True
    )
    notes = serializers.CharField(
        required=False,
        allow_blank=True,
        max_length=1000
    )

    def validate_status(self, value):
        """Validate status transition"""
        reservation = self.context.get('reservation')
        if not reservation:
            return value

        current_status = reservation.status

        # Không cho phép update nếu đã completed/cancelled
        if current_status in ['completed', 'cancelled']:
            raise serializers.ValidationError(
                f"Không thể thay đổi trạng thái từ '{reservation.get_status_display()}'"
            )

        # Validate luồng status hợp lệ
        valid_transitions = {
            'pending': ['confirmed', 'cancelled'],
            'confirmed': ['completed', 'cancelled'],
        }

        if current_status in valid_transitions:
            if value not in valid_transitions[current_status]:
                raise serializers.ValidationError(
                    f"Không thể chuyển từ '{reservation.get_status_display()}' sang '{dict(Reservation.STATUS_CHOICES).get(value)}'"
                )

        return value


class ReservationDepositPaymentSerializer(serializers.Serializer):
    """
    Serializer cho việc tạo payment cho reservation deposit
    Input: reservation_id + payment_method_id
    """
    reservation_id = serializers.IntegerField(required=True, help_text="ID reservation")
    payment_method_id = serializers.IntegerField(required=True, help_text="ID phương thức thanh toán")

    def validate_reservation_id(self, value):
        """Validate reservation exists và thuộc về user"""
        from apps.reservations.models import Reservation

        user = self.context.get('user')
        try:
            reservation = Reservation.objects.get(id=value)

            # Validate quyền sở hữu (staff có thể xem tất cả, customer chỉ xem của mình)
            if user.user_type != 'staff' and user.user_type != 'manager' and user.user_type != 'admin':
                if reservation.customer != user:
                    raise serializers.ValidationError(
                        "Bạn không có quyền truy cập reservation này."
                    )

            # Validate reservation chưa có payment
            if hasattr(reservation, 'payment') and reservation.payment:
                raise serializers.ValidationError(
                    "Reservation này đã có thanh toán cọc."
                )

            # Validate reservation status
            if reservation.status not in ['pending']:
                raise serializers.ValidationError(
                    f"Không thể thanh toán cọc cho reservation ở trạng thái '{reservation.get_status_display()}'."
                )

            return value
        except Reservation.DoesNotExist:
            raise serializers.ValidationError("Reservation không tồn tại.")

    def validate_payment_method_id(self, value):
        """Validate payment method exists và active"""
        from apps.payments.models import PaymentMethod

        try:
            payment_method = PaymentMethod.objects.get(id=value, is_active=True)
            return value
        except PaymentMethod.DoesNotExist:
            raise serializers.ValidationError(
                "Phương thức thanh toán không tồn tại hoặc không khả dụng."
            )


class ReservationCancelSerializer(serializers.Serializer):
    """
    Serializer cho việc hủy reservation
    """
    cancel_reason = serializers.CharField(
        required=True,
        allow_blank=False,
        max_length=500
    )

    def validate(self, attrs):
        """Validate có thể hủy reservation không"""
        reservation = self.context.get('reservation')
        if not reservation:
            return attrs

        # Chỉ cho phép hủy nếu status là pending hoặc confirmed
        if reservation.status not in ['pending', 'confirmed']:
            raise serializers.ValidationError(
                f"Không thể hủy reservation ở trạng thái '{reservation.get_status_display()}'"
            )

        # Nếu đã thanh toán cọc, cần phải refund trước
        if reservation.is_paid:
            raise serializers.ValidationError(
                "Reservation đã thanh toán cọc. Vui lòng hoàn tiền trước khi hủy."
            )

        return attrs


class TableStatusSerializer(serializers.Serializer):
    """
    Serializer cho trạng thái bàn theo thời gian
    """
    table_id = serializers.IntegerField()
    table_number = serializers.CharField()
    floor = serializers.IntegerField()
    section = serializers.CharField(allow_null=True)
    capacity = serializers.IntegerField()
    current_status = serializers.CharField()
    status_display = serializers.CharField()
    is_available = serializers.BooleanField()
    reservations = serializers.ListField(child=serializers.DictField())
    x_position = serializers.DecimalField(max_digits=10, decimal_places=2, allow_null=True)
    y_position = serializers.DecimalField(max_digits=10, decimal_places=2, allow_null=True)
