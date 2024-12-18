import logging
import frappe
from biometric_integration.services.device_mapping import get_site_for_device

def init_site_for_device(device_id: str):
    """
    Initialize the Frappe environment for the site corresponding to the given device_id.
    If the site cannot be resolved, raise an exception.

    Args:
        device_id (str): The ID of the biometric device.

    Raises:
        ValueError: If site cannot be resolved for the given device_id.
    """
    if not device_id:
        raise ValueError("Device ID is required to initialize site.")

    site_name = get_site_for_device(device_id)
    if not site_name:
        logging.error(f"Unable to resolve site for device ID {device_id}")
        raise ValueError(f"No site mapping found for device_id: {device_id}")

    # Initialize and connect to the resolved site
    frappe.init(site=site_name)
    frappe.connect()
    # Set an appropriate user
    frappe.set_user('Administrator')
    logging.info(f"Site context initialized for device {device_id} on site {site_name}")


def destroy_site():
    """
    Destroy the current Frappe site context, if initialized.
    If no site context is active, this does nothing.
    """
    try:
        frappe.destroy()
        logging.info("Site context destroyed.")
    except Exception as e:
        # If frappe wasn't initialized or any other issue occurred
        logging.debug(f"No active site context to destroy or error occurred: {str(e)}")