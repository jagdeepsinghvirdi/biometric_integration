import logging
import frappe
import base64
import os

def process_device_command(device_id):
    """
    Process the next available command for the given biometric device.

    Args:
        device_id (str): The ID of the biometric device.

    Returns:
        dict: Contains command data if a command was processed, otherwise None.
    """
    try:
        # Check for the next pending or reattempt command
        command_name = frappe.db.exists("Biometric Device Command", {"biometric_device": device_id, "status": ["in", ["Pending", "Reattempt"]]})
        if not command_name:
            logging.info(f"No pending or reattempt commands found for device {device_id}.")
            update_has_pending_command(device_id, 0)
            return None

        # Fetch the command document
        command_doc = frappe.get_doc("Biometric Device Command", command_name)
        return prepare_command_data(command_doc)

    except Exception as e:
        logging.error(f"Error processing device command for device {device_id}: {str(e)}", exc_info=True)
        return None

def handle_device_response(device_id, trans_id, cmd_return_code):
    """
    Handle the response from the device after receiving a chunk.

    Args:
        device_id (str): The ID of the biometric device.
        trans_id (str): The transaction ID associated with the command.
        cmd_return_code (str): The return code from the device.

    Returns:
        dict: The next chunk data or confirmation of completion.
    """
    try:
        # Fetch the command document
        command_doc = frappe.get_doc("Biometric Device Command", trans_id)

        if cmd_return_code != "OK":
            logging.error(f"Device {device_id} reported error for command {trans_id}. Return code: {cmd_return_code}")
            command_doc.status = "Error"
            command_doc.device_response = cmd_return_code
            command_doc.save()
            frappe.db.commit()
            return {"response_code": "ERROR"}

        # Prepare and send the next chunk
        next_chunk_data = prepare_command_data(command_doc)
        if next_chunk_data:
            logging.info(f"Sending next chunk for command {trans_id} to device {device_id}.")
            return next_chunk_data

        logging.info(f"All chunks for command {trans_id} sent to device {device_id}. Command completed.")
        command_doc.status = "Completed"
        command_doc.device_response = "Success"
        command_doc.save()
        frappe.db.commit()
        return {"response_code": "OK"}

    except Exception as e:
        logging.error(f"Error handling response for device {device_id} and command {trans_id}: {str(e)}", exc_info=True)
        return {"response_code": "ERROR"}

def update_has_pending_command(device_id, has_pending_command):
    """
    Update the has_pending_command field for the given biometric device.

    Args:
        device_id (str): The ID of the biometric device.
        has_pending_command (int): The value to set (0 or 1).
    """
    try:
        device_doc = frappe.get_doc("Biometric Device", device_id)
        device_doc.has_pending_command = has_pending_command
        device_doc.save()
        frappe.db.commit()
        logging.info(f"Updated has_pending_command for device {device_id} to {has_pending_command}.")
    except Exception as e:
        logging.error(f"Error updating has_pending_command for device {device_id}: {str(e)}", exc_info=True)

def prepare_command_data(command_doc):
    """
    Prepare the command data to be sent to the device processor in chunks.

    Args:
        command_doc (Document): The Biometric Device Command document.

    Returns:
        dict: Prepared command data.
    """
    if command_doc.brand == "EBKN" and command_doc.command_type == "Enroll User":
        # Fetch the binary enroll data attachment
        device_user = frappe.get_doc("Biometric Device User", command_doc.biometric_device_user)
        file_url = device_user.ebkn_enroll_data

        # Determine the file path
        if file_url.startswith("/private"):
            file_url_path = ("private", file_url.lstrip("/private/"))
        else:
            file_url_path = ("public", file_url.lstrip("/public/"))

        # Construct the full path using bench path
        file_path = os.path.join(frappe.utils.get_bench_path(), "sites", frappe.get_site_path(*file_url_path))

        # Read the binary file content
        try:
            with open("/home/zima/frappe-bench/sites/erpc.zimallc.com/public/file/b1c8f84c49/enroll_data_11d674a.bin", "rb") as f:
                data_bytes = f.read()
        except FileNotFoundError:
            logging.error(f"File not found at {file_path}")
            raise

        # Split data into chunks
        max_chunk_size = 1024  # Define chunk size limit
        chunks = [data_bytes[i:i + max_chunk_size] for i in range(0, len(data_bytes), max_chunk_size)]

        # Determine next chunk to send
        last_sent = command_doc.last_sent_data_block or 0
        if last_sent >= len(chunks):
            logging.info(f"All chunks sent for command {command_doc.name}.")
            return None

        next_chunk = chunks[last_sent]

        # Check if this is the final block
        is_last_block = (last_sent == len(chunks) - 1)
        blk_no = 0 if is_last_block else last_sent + 1

        # Update command document with the last sent block
        command_doc.last_sent_data_block = blk_no
        command_doc.save()
        frappe.db.commit()

        return {
            "trans_id": command_doc.name,
            "cmd_code": "SET_USER_INFO",
            "blk_no": blk_no,
            "body": base64.b64encode(next_chunk).decode("utf-8")
        }

    return None
