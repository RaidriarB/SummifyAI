import json
import os
import time
import uuid


RECORDS_VERSION = 2


def generate_file_id():
    return uuid.uuid4().hex


def compute_base_name(filename, allowed_exts):
    if not filename:
        return filename
    base, ext = os.path.splitext(filename)
    if ext.lower() in allowed_exts:
        return base
    return filename


def load_records(path):
    if os.path.exists(path):
        try:
            with open(path, "r", encoding="utf-8") as f:
                data = json.load(f)
                if isinstance(data, dict) and isinstance(data.get("records", []), list):
                    return data
        except Exception:
            pass
    return {"version": RECORDS_VERSION, "records": []}


def save_records(path, data):
    os.makedirs(os.path.dirname(path), exist_ok=True)
    with open(path, "w", encoding="utf-8") as f:
        json.dump(data, f, indent=2, ensure_ascii=False)


def normalize_record(record, allowed_exts):
    if not isinstance(record, dict):
        return None
    file_name = record.get("file_name")
    if not isinstance(file_name, str) or not file_name.strip():
        return None
    stored_name = record.get("stored_name") or file_name
    record_id = record.get("id") or file_name
    output_folder = record.get("output_folder") or compute_base_name(file_name, allowed_exts)
    return {
        "id": record_id,
        "file_name": file_name,
        "stored_name": stored_name,
        "output_folder": output_folder,
        "transcribed": record.get("transcribed", False),
        "fixed": record.get("fixed", False),
        "summarized": record.get("summarized", False),
        "last_time": record.get("last_transcription_time"),
        "last_fix_time": record.get("last_fix_time"),
        "last_summary_time": record.get("last_summary_time"),
        "created_time": record.get("created_time"),
        "raw": record,
    }


def find_record(data, file_id=None, filename=None):
    if not isinstance(data, dict):
        return None
    items = data.get("records", [])
    if file_id:
        for record in items:
            if isinstance(record, dict) and record.get("id") == file_id:
                return record
    if filename:
        for record in items:
            if isinstance(record, dict) and record.get("file_name") == filename:
                return record
    return None


def migrate_records(data, upload_dir, output_dir, allowed_exts):
    changed = False
    if not isinstance(data, dict):
        data = {"version": RECORDS_VERSION, "records": []}
        changed = True
    records = []
    for record in data.get("records", []):
        if not isinstance(record, dict):
            changed = True
            continue
        file_name = record.get("file_name")
        if not isinstance(file_name, str) or not file_name.strip():
            changed = True
            continue
        record = dict(record)
        if not record.get("id"):
            record["id"] = generate_file_id()
            changed = True
        stored_name = record.get("stored_name")
        if not isinstance(stored_name, str) or not stored_name.strip():
            stored_name = file_name
            record["stored_name"] = stored_name
            changed = True
        record_id = record["id"]
        desired_stored = f"{record_id}__{file_name}"
        if upload_dir and os.path.exists(upload_dir):
            stored_path = os.path.join(upload_dir, stored_name)
            desired_path = os.path.join(upload_dir, desired_stored)
            if stored_name != desired_stored:
                if os.path.exists(stored_path) and not os.path.exists(desired_path):
                    try:
                        os.replace(stored_path, desired_path)
                        record["stored_name"] = desired_stored
                        changed = True
                    except Exception:
                        pass
        output_folder = record.get("output_folder")
        desired_output = record_id
        if not isinstance(output_folder, str) or not output_folder.strip():
            output_folder = compute_base_name(file_name, allowed_exts)
            record["output_folder"] = output_folder
            changed = True
        if output_dir and os.path.exists(output_dir):
            old_out = os.path.join(output_dir, output_folder)
            new_out = os.path.join(output_dir, desired_output)
            if output_folder != desired_output and os.path.exists(old_out) and not os.path.exists(new_out):
                try:
                    os.replace(old_out, new_out)
                    record["output_folder"] = desired_output
                    changed = True
                    output_folder = desired_output
                except Exception:
                    pass
            # normalize output filenames from stored_name to display name
            out_dir = os.path.join(output_dir, record.get("output_folder") or output_folder)
            if os.path.exists(out_dir):
                for fname in os.listdir(out_dir):
                    new_name = None
                    if stored_name and fname.startswith(stored_name):
                        new_name = file_name + fname[len(stored_name):]
                    elif fname.startswith(os.path.splitext(stored_name)[0]):
                        new_name = os.path.splitext(file_name)[0] + fname[len(os.path.splitext(stored_name)[0]):]
                    if new_name:
                        try:
                            os.replace(os.path.join(out_dir, fname), os.path.join(out_dir, new_name))
                            changed = True
                        except Exception:
                            pass
        if not record.get("created_time"):
            record["created_time"] = time.strftime("%Y-%m-%d %H:%M:%S")
            changed = True
        if "fixed" not in record:
            record["fixed"] = False
            changed = True
        if "summarized" not in record:
            record["summarized"] = False
            changed = True
        if "last_fix_time" not in record:
            record["last_fix_time"] = None
            changed = True
        if "last_summary_time" not in record:
            record["last_summary_time"] = None
            changed = True
        records.append(record)
    if data.get("version") != RECORDS_VERSION:
        data["version"] = RECORDS_VERSION
        changed = True
    data["records"] = records
    return data, changed


def upsert_record(data, file_name, file_id=None, stored_name=None, output_folder=None,
                  transcribed=None, fixed=None, summarized=None,
                  last_time=None, last_fix_time=None, last_summary_time=None,
                  created_time=None):
    record = find_record(data, file_id=file_id, filename=file_name)
    if record is None:
        record = {
            "file_name": file_name,
            "transcribed": False,
            "last_transcription_time": None,
            "created_time": created_time or time.strftime("%Y-%m-%d %H:%M:%S"),
        }
        data["records"].append(record)
    if file_id:
        record["id"] = file_id
    if stored_name:
        record["stored_name"] = stored_name
    if output_folder:
        record["output_folder"] = output_folder
    if created_time and not record.get("created_time"):
        record["created_time"] = created_time
    if transcribed is not None:
        record["transcribed"] = transcribed
    if fixed is not None:
        record["fixed"] = fixed
    if summarized is not None:
        record["summarized"] = summarized
    if last_time is not None:
        record["last_transcription_time"] = last_time
    if last_fix_time is not None:
        record["last_fix_time"] = last_fix_time
    if last_summary_time is not None:
        record["last_summary_time"] = last_summary_time
    return record


def sync_with_upload(data, upload_dir, allowed_exts):
    changed = False
    if not upload_dir or not os.path.exists(upload_dir):
        return data, changed
    for file in os.listdir(upload_dir):
        if not isinstance(file, str):
            continue
        if os.path.splitext(file)[1].lower() not in allowed_exts:
            continue
        if file.endswith("_转写.txt"):
            continue
        record = find_record(data, file_id=file, filename=file)
        if record:
            continue
        file_id = None
        display_name = file
        if "__" in file:
            prefix, rest = file.split("__", 1)
            if len(prefix) == 32 and all(c in "0123456789abcdef" for c in prefix.lower()):
                file_id = prefix
                display_name = rest or file
        if not file_id:
            file_id = generate_file_id()
            desired_name = f"{file_id}__{display_name}"
            desired_path = os.path.join(upload_dir, desired_name)
            current_path = os.path.join(upload_dir, file)
            if not os.path.exists(desired_path):
                try:
                    os.replace(current_path, desired_path)
                    file = desired_name
                except Exception:
                    pass
        upsert_record(
            data,
            file_name=display_name,
            file_id=file_id,
            stored_name=file,
            output_folder=file_id,
            created_time=time.strftime("%Y-%m-%d %H:%M:%S"),
        )
        changed = True
    return data, changed


def list_records(data, upload_dir, allowed_exts):
    items = []
    for record in data.get("records", []):
        norm = normalize_record(record, allowed_exts)
        if not norm:
            continue
        stored_name = norm["stored_name"]
        if upload_dir and not os.path.exists(os.path.join(upload_dir, stored_name)):
            continue
        items.append(norm)
    items.sort(key=lambda x: x.get("created_time") or "", reverse=True)
    return items
