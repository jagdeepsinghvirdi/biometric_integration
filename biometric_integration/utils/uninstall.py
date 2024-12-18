import os
import frappe
import logging
import shutil
from frappe.utils import get_sites

def cleanup():
    """Cleanup assets directory created by the biometric_integration app only if no site uses it."""
    app_name = "biometric_integration"
    try:
        # Check all sites
        found_app_in_site = False
        for site in get_sites():
            frappe.init(site=site)
            frappe.connect()
            installed_apps = frappe.get_installed_apps()
            frappe.destroy()

            if app_name in installed_apps:
                found_app_in_site = True
                logging.info(f"App {app_name} is still installed in site {site}, not removing assets.")
                break

        if not found_app_in_site:
            # No site has the app installed, proceed with cleanup
            assets_dir = frappe.get_site_path("assets", "biometric_assets")
            if os.path.exists(assets_dir):
                shutil.rmtree(assets_dir)
                logging.info("biometric_assets directory removed successfully.")
            else:
                logging.info("biometric_assets directory does not exist, no cleanup needed.")

    except Exception as e:
        logging.error(f"Error while cleaning up biometric_assets directory: {str(e)}")
