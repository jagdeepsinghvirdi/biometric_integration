import logging
import frappe
from biometric_integration.services.device_mapping import get_site_for_device

def init_site(device_id: str = None, site_name: str = None):
    """
    Initialize the Frappe environment for the site corresponding to the given device_id or site_name.
    If both are provided, site_name takes precedence. If neither resolves, raise an exception.

    Args:
        device_id (str): The ID of the biometric device (optional).
        site_name (str): The name of the site (optional).

    Returns:
        bool: True if the site context is successfully initialized.

    Raises:
        ValueError: If neither site_name nor device_id can resolve a site.
    """
    if not site_name:
        if not device_id:
            raise ValueError("Either site_name or device_id is required to initialize site.")

        device_info = get_site_for_device(device_id)

        if not device_info or not device_info.get("site_name"):
            raise ValueError(f"No site mapping found for device_id: {device_id}")
        
        if device_info.get("disabled"):
            raise ValueError(f"Device with {device_id} is disabled. Cannot initialize site.")
        
        site_name = device_info["site_name"]

    # Initialize and connect to the resolved site
    frappe.init(site=site_name)
    frappe.connect()
    # Set an appropriate user
    frappe.set_user('Administrator')
    logging.info(f"Site context initialized for site {site_name}")

    return True

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