# Biometric Device Integration for Frappe

This Frappe app integrates popular biometric devices like EBKN, Suprema, and ZKTeco with Frappe HRMS, enabling real-time or scheduled synchronization of attendance logs. It also allows creating and updating device users directly from the ERP.

**⚠ Warning: This is an under-development project and is not ready for production use..**

## Features
- **Real-time Attendance Sync**: Process logs as soon as they are sent by devices.
- **Scheduled Synchronization**: Set up periodic (cron-based) synchronization for devices that do not support push protocols.
- **User Management**: Create or update users on biometric devices directly from Frappe ERP.
- **Device Compatibility**: Supports EBKN, Suprema, and ZKTeco devices, with options for easy extensibility to other brands.

## Supported Brands
### EBKN
- Supports push protocols for real-time attendance log synchronization.
- Allows device commands and user management directly from ERP.

### Suprema
- Configured for scheduled or real-time log synchronization.
- ERP handles device configuration automatically.

### ZKTeco
- Supports both real-time push and scheduled synchronization.
- Compatible with the ADMS protocol for attendance management.
