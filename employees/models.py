from django.core.validators import MinValueValidator,MaxValueValidator
from django.contrib.auth.models import User
from django.db import models


class Employee(models.Model):
 
       user = models.OneToOneField(
            User,
            on_delete=models.CASCADE,
            related_name="employee_profile",
            null=True,
            blank=True
        )
       employee_id = models.CharField(max_length=20, unique=True)
       name = models.CharField(max_length=100)
       email = models.EmailField(unique=True)
       phone = models.CharField(max_length=15)
       department = models.CharField(max_length=100)
       designation = models.CharField(max_length=100)

       def __str__(self):
          return f"{self.employee_id} - {self.name}"
       
class Robot(models.Model):
    robot_id = models.CharField(max_length=50, unique=True)

    employee = models.ForeignKey(
        Employee,
        on_delete=models.PROTECT,
        related_name="robots"
    )

    battery_percentage = models.PositiveSmallIntegerField(
        default=100,
        validators=[
            MinValueValidator(0),
            MaxValueValidator(100),
        ]
    )

    status = models.CharField(
     max_length=20,
     default="Active"
    )
    
    created_at = models.DateTimeField(auto_now_add=True)

    def __str__(self):
        return self.robot_id


# Create your models here.
