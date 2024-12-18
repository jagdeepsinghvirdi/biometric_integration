from biometric_integration.services.create_checkin import create_employee_checkin
from datetime import datetime
import logging
import json
import re
import base64
import os
import frappe

def parse_device_data(raw_data: bytes) -> dict:
    text = raw_data.decode('utf-8', errors='replace')

    start_idx = text.find('{')
    if start_idx == -1:
        raise ValueError("No JSON object start found (no '{').")

    # Find balanced braces
    brace_count = 0
    json_end = -1
    for i, ch in enumerate(text[start_idx:], start=start_idx):
        if ch == '{':
            brace_count += 1
        elif ch == '}':
            brace_count -= 1
            if brace_count == 0:
                json_end = i
                break

    if json_end == -1:
        raise ValueError("Could not find a balanced JSON object.")

    json_str = text[start_idx:json_end+1]
    data = json.loads(json_str)

    binary_data = raw_data[json_end+1:]

    def find_bin_placeholders(obj, bins_found=None):
        if bins_found is None:
            bins_found = []
        if isinstance(obj, dict):
            for k, v in obj.items():
                if isinstance(v, str) and v.startswith("BIN_"):
                    bins_found.append(v)
                else:
                    find_bin_placeholders(v, bins_found)
        elif isinstance(obj, list):
            for item in obj:
                find_bin_placeholders(item, bins_found)
        return bins_found

    bin_placeholders = find_bin_placeholders(data)

    if bin_placeholders:
        count = len(bin_placeholders)
        if count > 0:
            segment_size = len(binary_data) // count if count else 0
            bin_segments = []
            start = 0
            for i in range(count):
                if i == count - 1:
                    seg = binary_data[start:]
                else:
                    seg = binary_data[start:start+segment_size]
                start += segment_size
                bin_segments.append(seg)

            bin_map = dict(zip(bin_placeholders, bin_segments))

            def replace_bins(obj):
                if isinstance(obj, dict):
                    for k, v in obj.items():
                        if isinstance(v, str) and v.startswith("BIN_"):
                            if v in bin_map:
                                obj[k] = base64.b64encode(bin_map[v]).decode('ascii')
                            else:
                                obj[k] = None
                        else:
                            replace_bins(v)
                elif isinstance(obj, list):
                    for i, item in enumerate(obj):
                        if isinstance(item, str) and item.startswith("BIN_"):
                            if item in bin_map:
                                obj[i] = base64.b64encode(bin_map[item]).decode('ascii')
                            else:
                                obj[i] = None
                        else:
                            replace_bins(item)

            replace_bins(data)

    return data

def get_biometric_assets_dir():
    # Get bench path (e.g. /home/zima/frappe-bench)
    bench_path = frappe.utils.get_bench_path()
    # Construct the path without using get_site_path, which requires site context
    assets_dir = os.path.join(bench_path, "sites", "assets", "biometric_assets")
    os.makedirs(assets_dir, exist_ok=True)
    return assets_dir

def get_partial_data_dir():
    assets_dir = get_biometric_assets_dir()
    partial_dir = os.path.join(assets_dir, "partial_data")
    os.makedirs(partial_dir, exist_ok=True)
    return partial_dir

def get_block_sequence_map_path():
    assets_dir = get_biometric_assets_dir()
    return os.path.join(assets_dir, "block_sequence_map.json")

def load_block_sequence_map():
    file_path = get_block_sequence_map_path()
    if os.path.exists(file_path):
        try:
            with open(file_path, "r") as f:
                return json.load(f)
        except Exception as e:
            logging.error(f"Error loading block sequence map: {str(e)}")
            return {}
    else:
        return {}

def save_block_sequence_map(seq_map):
    file_path = get_block_sequence_map_path()
    try:
        with open(file_path, "w") as f:
            json.dump(seq_map, f, indent=4)
    except Exception as e:
        logging.error(f"Error saving block sequence map: {str(e)}")

def get_sequence_key(dev_id, request_code):
    return f"{dev_id}_{request_code}"

def get_last_block_no(dev_id, request_code):
    seq_map = load_block_sequence_map()
    key = get_sequence_key(dev_id, request_code)
    val = seq_map.get(key, None)
    return val

def set_last_block_no(dev_id, request_code, blk_no):
    seq_map = load_block_sequence_map()
    key = get_sequence_key(dev_id, request_code)
    seq_map[key] = blk_no
    save_block_sequence_map(seq_map)

def clear_sequence(dev_id, request_code):
    seq_map = load_block_sequence_map()
    key = get_sequence_key(dev_id, request_code)
    if key in seq_map:
        del seq_map[key]
    save_block_sequence_map(seq_map)

def get_partial_file_path(dev_id, request_code):
    filename = f"{dev_id}_{request_code}.bin"
    return os.path.join(get_partial_data_dir(), filename)

def start_new_sequence(dev_id, request_code):
    # If file exists, delete it to start fresh
    file_path = get_partial_file_path(dev_id, request_code)
    if os.path.exists(file_path):
        os.remove(file_path)
    # Reset block tracking in JSON map
    clear_sequence(dev_id, request_code)

def store_block(dev_id, request_code, raw_data):
    file_path = get_partial_file_path(dev_id, request_code)
    with open(file_path, 'ab') as f:
        f.write(raw_data)

def read_full_data(dev_id, request_code):
    file_path = get_partial_file_path(dev_id, request_code)
    if os.path.exists(file_path):
        with open(file_path, 'rb') as f:
            return f.read()
    return None

def clear_data(dev_id, request_code):
    file_path = get_partial_file_path(dev_id, request_code)
    if os.path.exists(file_path):
        os.remove(file_path)
    clear_sequence(dev_id, request_code)

def respond_after_block():
    response_headers = {
        "response_code": "OK"
    }
    # Body empty, return 200 with headers
    return "", 200, response_headers

def handle_ebkn(request, raw_data, headers):
    try:
        request_code = headers.get("request_code")
        dev_id = headers.get("dev_id")
        blk_no = headers.get("blk_no")

        if not request_code or not dev_id:
            logging.error("Missing request_code or dev_id.")
            return '{"error": "Missing request_code or dev_id"}', 400, {}

        logging.info(f"Request Code: {request_code}, Device ID: {dev_id}")

        # blk_no might be optional
        if blk_no is not None:
            blk_no = int(blk_no)
        else:
            # Single-block scenario
            blk_no = 0

        last_blk_no = get_last_block_no(dev_id, request_code)

        if blk_no == 1:
            # Start new sequence
            start_new_sequence(dev_id, request_code)
            store_block(dev_id, request_code, raw_data)
            set_last_block_no(dev_id, request_code, 1)
            return respond_after_block()

        elif blk_no > 1:
            # Continuation block
            if last_blk_no is None:
                logging.error("Received a continuation block without a start.")
                return '{"error": "Unexpected block sequence"}', 400, {}

            if blk_no != last_blk_no + 1:
                logging.error(f"Block sequence mismatch. Expected {last_blk_no+1}, got {blk_no}.")
                return '{"error": "Block sequence mismatch"}', 400, {}

            store_block(dev_id, request_code, raw_data)
            set_last_block_no(dev_id, request_code, blk_no)
            return respond_after_block()

        elif blk_no == 0:
            # Final block or single-block scenario
            if last_blk_no is None:
                # Single-block scenario
                full_data = raw_data
            else:
                if last_blk_no < 1:
                    logging.error("Final block received without initial blocks.")
                    return '{"error": "No initial block received"}', 400, {}

                store_block(dev_id, request_code, raw_data)
                set_last_block_no(dev_id, request_code, 0)
                full_data = read_full_data(dev_id, request_code)
                if not full_data:
                    logging.error("Could not read full data after final block.")
                    return '{"error": "Data reading error"}', 500, {}

            # Parse full data
            try:
                parsed_data = parse_device_data(full_data)
            except ValueError as ve:
                msg = str(ve)
                logging.error(f"Parsing error: {msg}")
                clear_data(dev_id, request_code)
                return '{"error": "Failed to parse data"}', 400, {}

            # Success, clear partial data
            clear_data(dev_id, request_code)

            parsed_data["device_id"] = dev_id

            # Route to brand-specific handlers
            if request_code == "realtime_glog":
                return handle_realtime_glog(parsed_data)
            elif request_code == "realtime_enroll_data":
                return handle_realtime_enroll_data(parsed_data)
            elif request_code == "receive_cmd":
                return handle_receive_cmd(parsed_data)
            elif request_code == "send_cmd_result":
                return handle_send_cmd_result(parsed_data)
            else:
                logging.warning(f"Unsupported request_code: {request_code}")
                return '{"error": "Unsupported request_code"}', 400, {}

        else:
            # Invalid blk_no
            logging.error(f"Invalid blk_no: {blk_no}")
            return '{"error": "Invalid block number"}', 400, {}

    except Exception as e:
        logging.error(f"Error in handle_ebkn: {str(e)}", exc_info=True)
        return '{"error": "Internal server error"}', 500, {}

def handle_receive_cmd(data):
    try:
        trans_id = data.get("trans_id", "0")
        cmd_code = ""

        response_headers = {
            "response_code": "OK",
            "trans_id": trans_id,
            "cmd_code": cmd_code,
        }
        return "", 200, response_headers

    except Exception as e:
        logging.error(f"Error in handle_receive_cmd: {str(e)}", exc_info=True)
        return '{"error": "Internal server error"}', 500, {}

def handle_send_cmd_result(data):
    try:
        cmd_result = data.get("cmd_result", "UNKNOWN")
        logging.info(f"Command Result: {cmd_result}")

        # Just an example
        return '{"response_code": "OK"}', 200, {}

    except Exception as e:
        logging.error(f"Error in handle_send_cmd_result: {str(e)}", exc_info=True)
        return '{"error": "Internal server error"}', 500, {}

def handle_realtime_glog(data):
    try:
        user_id = data.get("user_id")
        io_time = data.get("io_time")
        io_mode = data.get("io_mode")
        device_id = data.get("device_id")

        if not user_id or not io_time:
            logging.error("Missing required fields in realtime_glog")
            return '{"error": "Missing required fields"}', 400, {"response_code": "ERROR"}

        try:
            employee_field_value = int(user_id)
        except ValueError:
            logging.error(f"Invalid user_id format: {user_id}")
            return '{"error": "Invalid user_id format"}', 400, {"response_code": "ERROR"}

        timestamp = datetime.strptime(io_time, "%Y%m%d%H%M%S").strftime("%Y-%m-%d %H:%M:%S")
        log_type = "IN" if io_mode == 1 else "OUT"

        is_success = create_employee_checkin(
            employee_field_value=employee_field_value,
            timestamp=timestamp,
            device_id=str(device_id),
            log_type=log_type,
        )

        if is_success:
            logging.info(f"Realtime log processed for user {employee_field_value} at {timestamp}")
            return '{"response_code": "OK"}', 200, {"response_code": "OK"}
        else:
            logging.error(f"Failed to process realtime log for user {employee_field_value}")
            return '{"response_code": "ERROR"}', 500, {"response_code": "ERROR"}

    except Exception as e:
        logging.error(f"Error handling realtime_glog: {str(e)}", exc_info=True)
        return '{"error": "Internal server error"}', 500, {"response_code": "ERROR"}

def handle_realtime_enroll_data(data):
    try:
        trans_id = data.get("trans_id", "0")
        cmd_code = ""

        response_headers = {
            "response_code": "OK",
            "trans_id": trans_id,
            "cmd_code": cmd_code,
        }

        return "", 200, response_headers

    except Exception as e:
        logging.error(f"Error in handle_realtime_enroll_data: {str(e)}", exc_info=True)
        return '{"error": "Internal server error"}', 500, {}
