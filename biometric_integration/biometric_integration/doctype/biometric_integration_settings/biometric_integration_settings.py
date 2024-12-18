# Copyright (c) 2024, KhaledBinAmir and contributors
# For license information, please see license.txt

import re
import frappe
import random

class BiometricIntegrationSettings(Document):
    def validate(self):
        """
        Validate the Biometric Integration Settings document.
        Ensure required fields are properly configured based on the selected mapping method.
        """
        if self.employee_id_mapping_method == "Use Device ID Field" and not self.device_id_field:
            frappe.throw("Device ID Field is required when using the 'Use Device ID Field' mapping method.")

        if self.employee_id_mapping_method == "Clean Employee ID with Regex" and not self.clean_id_regex:
            frappe.throw("Clean ID Regex is required when using the 'Clean Employee ID with Regex' mapping method.")

        if self.clean_id_regex:
            try:
                re.compile(self.clean_id_regex)
            except re.error:
                frappe.throw(f"The provided Clean ID Regex '{self.clean_id_regex}' is not a valid regex pattern.")

    def before_save(self):
        """
        Actions to perform before saving the document.
        """
        employee_ids = frappe.get_all("Employee", fields=["name"], limit=30)
        if not employee_ids:
            self.example_cleaned_ids = "No employees found to clean."
            return

        random_ids = random.sample(employee_ids, min(len(employee_ids), 5))  # Pick 5 random employees
        cleaned_ids = []

        for emp in random_ids:
            cleaned_id = re.sub(self.clean_id_regex, "", emp["name"])
            cleaned_ids.append(f"{emp['name']} -> {cleaned_id}")

        self.example_cleaned_ids = "\n".join(cleaned_ids)

def get_device_employee_id(employee_id):
    """
    Convert an ERP Employee ID to a Device Employee ID based on the mapping method.

    Args:
        employee_id (str): The ERP Employee ID.

    Returns:
        str: The Device Employee ID.
    """
    if not employee_id:
        frappe.throw("Employee ID is required.")

    settings = frappe.get_cached_doc("Biometric Integration Settings")

    if settings.employee_id_mapping_method == "Use Device ID Field":
        device_employee_id = frappe.get_value("Employee", {"name": employee_id}, settings.device_id_field)
        if not device_employee_id:
            frappe.throw(f"Device Employee ID not found for Employee {employee_id} in field '{settings.device_id_field}'.")
        return device_employee_id

    elif settings.employee_id_mapping_method == "Clean Employee ID with Regex":
        if not settings.clean_id_regex:
            frappe.throw("Clean ID Regex is not configured.")
        cleaned_id = re.sub(settings.clean_id_regex, "", employee_id)
        if not cleaned_id:
            frappe.throw(f"Failed to clean Employee ID '{employee_id}' using regex '{settings.clean_id_regex}'.")
        return cleaned_id

    frappe.throw(f"Unsupported mapping method: {settings.employee_id_mapping_method}")

def get_erp_employee_id(device_employee_id):
    """
    Convert a Device Employee ID to an ERP Employee ID based on the mapping method.

    Args:
        device_employee_id (str): The Device Employee ID.

    Returns:
        str: The ERP Employee ID.
    """
    if not device_employee_id:
        frappe.throw("Device Employee ID is required.")

    settings = frappe.get_cached_doc("Biometric Integration Settings")

    if settings.employee_id_mapping_method == "Use Device ID Field":
        erp_employee_id = frappe.get_value("Employee", {settings.device_id_field: device_employee_id}, "name")
        if not erp_employee_id:
            frappe.throw(f"ERP Employee ID not found for Device Employee ID '{device_employee_id}' in field '{settings.device_id_field}'.")
        return erp_employee_id

    elif settings.employee_id_mapping_method == "Clean Employee ID with Regex":
        erp_employee_id = frappe.get_value("Employee", {"name": device_employee_id}, "name")
        if not erp_employee_id:
            frappe.throw(f"ERP Employee ID not found for cleaned ID '{device_employee_id}'.")
        return erp_employee_id

    frappe.throw(f"Unsupported mapping method: {settings.employee_id_mapping_method}")