import logging
import json

def parse_incoming_data(raw_data):
    """
    Parse incoming raw data to extract and decode the JSON portion.

    Args:
        raw_data (bytes): Raw binary data from the request body.

    Returns:
        dict: Parsed JSON data as a Python dictionary, or an empty dictionary if parsing fails.
    """
    try:
        # Locate the first '{' and the last '}'
        json_start_index = raw_data.find(b'{')
        json_end_index = raw_data.rfind(b'}') + 1

        if json_start_index != -1 and json_end_index != -1:
            # Extract and decode the JSON portion
            json_data = raw_data[json_start_index:json_end_index].decode('utf-8', errors='ignore')
            parsed_data = json.loads(json_data)
            logging.info(f"Parsed JSON Data: {parsed_data}")
            return parsed_data
        else:
            logging.error(f"Failed to locate valid JSON structure. Raw Data: {raw_data}")
            return {}

    except (ValueError, json.JSONDecodeError) as e:
        logging.error(f"JSON parsing error: {str(e)}. Raw Data: {raw_data}")
        return {}


def handle_ebkn(request, raw_data):
    """
    Handles EBKN-specific requests with robust JSON parsing.

    Args:
        request: The HTTP request object.
        raw_data (bytes): Raw binary data from the request body.

    Returns:
        tuple: A response body (str) and HTTP status code (int).
    """
    try:
        # Extract headers
        headers = request.headers
        request_code = headers.get("request_code")
        logging.info(f"Request Code: {request_code}")

        if not request_code:
            logging.error("Missing request_code in headers")
            return '{"error": "Missing request_code"}', 400

        # Parse the incoming data
        payload = parse_incoming_data(raw_data)
        if not payload:
            return '{"error": "Invalid or missing JSON payload"}', 400

        # Process based on request_code
        if request_code == "receive_cmd":
            return handle_receive_cmd(payload)
        else:
            logging.warning(f"Unsupported request_code: {request_code}")
            return f'{{"error": "Unsupported request_code: {request_code}"}}', 400

    except Exception as e:
        logging.error(f"Error in handle_ebkn: {str(e)}", exc_info=True)
        return '{"error": "Internal server error"}', 500


def handle_receive_cmd(payload):
    """
    Handle 'receive_cmd' request_code by responding with no command available.

    Args:
        payload (dict): Parsed JSON payload from the device request.

    Returns:
        tuple: A response body (str) and HTTP status code (int).
    """
    try:
        # Extract device information
        fk_name = payload.get("fk_name")
        fk_time = payload.get("fk_time")
        fk_info = payload.get("fk_info")
        trans_id = payload.get("trans_id", "0")  # Use default trans_id if not provided

        if not fk_name or not fk_time:
            return '{"error": "Missing required fields"}', 400

        # Log the device information for debugging
        logging.info(f"Device {fk_name} requested instructions at {fk_time}")
        logging.info(f"Device Info: {fk_info}")

        # Create the response headers
        response_headers = {
            "response_code": "OK",
            "trans_id": trans_id,
            "Content-Type": "application/octet-stream",
        }

        # Response body: Empty for no command available
        response_body = '{}'

        # Return the headers and body
        return json.dumps(response_headers), 200

    except Exception as e:
        logging.error(f"Error in handle_receive_cmd: {str(e)}", exc_info=True)
        return '{"error": "Internal server error"}', 500