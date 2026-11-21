from django.db import models


class Location(models.Model):
    """
    Location master table.
    The single source of truth linking locations to organizations (tenants).
    """
    location_id = models.CharField(max_length=50, unique=True, primary_key=True)
    org_id = models.CharField(max_length=50, db_index=True)
    name = models.CharField(max_length=150)

    class Meta:
        ordering = ['location_id']

    def __str__(self):
        return f"{self.location_id} ({self.org_id})"


class SystemARecord(models.Model):
    """
    Records as maintained in System A.
    """
    record_id = models.CharField(max_length=50, unique=True, primary_key=True)
    location = models.ForeignKey(Location, on_delete=models.PROTECT, related_name='system_a_records')
    event_date = models.DateField()
    category_code = models.CharField(max_length=50)
    actor_id = models.CharField(max_length=50, null=True, blank=True)
    base_value = models.DecimalField(max_digits=14, decimal_places=2)
    adjustment = models.DecimalField(max_digits=14, decimal_places=2)
    total_value = models.DecimalField(max_digits=14, decimal_places=2)
    state = models.CharField(max_length=20)

    class Meta:
        ordering = ['record_id']

    def __str__(self):
        return f"{self.record_id} [{self.state}] {self.total_value}"


class SystemBEntry(models.Model):
    """
    Entries as maintained in System B.
    Notice: No foreign key to SystemARecord because orphan entries exist in B
    pointing to non-existent records in A. Also, multiple entries can share
    the same record_ref (e.g. split transactions or duplicates).
    Raw strings are preserved so no dirty data is lost.
    """
    entry_id = models.CharField(max_length=50, unique=True, primary_key=True)
    record_ref_raw = models.CharField(max_length=100)
    record_ref = models.CharField(max_length=50, null=True, blank=True, db_index=True)
    location = models.ForeignKey(Location, on_delete=models.PROTECT, related_name='system_b_entries')
    recorded_on = models.DateField()
    value_raw = models.CharField(max_length=100, blank=True)
    value = models.DecimalField(max_digits=14, decimal_places=2, null=True, blank=True)
    label = models.CharField(max_length=255, blank=True)

    class Meta:
        ordering = ['entry_id']

    def __str__(self):
        return f"{self.entry_id} -> {self.record_ref} ({self.value})"
