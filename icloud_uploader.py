"""
Upload media files to iCloud Photos using pyicloud library.
"""
import logging
import os
import time
from pathlib import Path
from typing import List, Dict, Optional, Callable
from pyicloud import PyiCloudService
from pyicloud.exceptions import PyiCloudFailedLoginException, PyiCloud2SARequiredException, PyiCloud2FARequiredException
from tqdm import tqdm

logger = logging.getLogger(__name__)


class iCloudUploader:
    """Handles uploading media files to iCloud Photos."""
    
    def __init__(self, apple_id: str, password: str, 
                 trusted_device_id: Optional[str] = None,
                 two_fa_code: Optional[str] = None):
        """
        Initialize the iCloud uploader.
        
        Args:
            apple_id: Apple ID email
            password: Apple ID password (empty string will prompt)
            trusted_device_id: Optional trusted device ID for 2FA
            two_fa_code: Optional 2FA verification code (for non-interactive use)
                         Can also be set via ICLOUD_2FA_CODE environment variable
        """
        self.apple_id = apple_id
        # Strip password but preserve it - don't convert empty string to None
        self.password = password.strip() if password else ''
        self.trusted_device_id = trusted_device_id
        # Support 2FA code from parameter, env var, or None for interactive
        self.two_fa_code = two_fa_code or os.environ.get('ICLOUD_2FA_CODE')
        if self.two_fa_code:
            self.two_fa_code = self.two_fa_code.strip().replace(' ', '').replace('-', '')
        # Also check for trusted_device_id in env if not provided
        if not self.trusted_device_id:
            self.trusted_device_id = os.environ.get('ICLOUD_2FA_DEVICE_ID')
        self.api = None
        
        # Prompt for password if empty
        if not self.password:
            import getpass
            logger.info("iCloud password not provided. Please enter your Apple ID password:")
            logger.info("(Note: If you have 2FA enabled, use your regular password)")
            self.password = getpass.getpass("Password: ").strip()
        
        # Validate that we have both apple_id and password
        if not self.apple_id:
            raise ValueError("Apple ID is required")
        if not self.password:
            raise ValueError("Password is required")
        
        self._authenticate()
    
    def _authenticate(self, clear_cookies: bool = False):
        """Authenticate with iCloud.
        
        Args:
            clear_cookies: If True, clear existing cookies before authenticating
        """
        try:
            # Use a cookie directory in the user's home directory to avoid permission issues
            cookie_dir = os.path.expanduser("~/.pyicloud")
            
            # Clear cookies if requested (useful for troubleshooting)
            if clear_cookies and os.path.exists(cookie_dir):
                import shutil
                logger.info(f"Clearing existing cookies from {cookie_dir}")
                shutil.rmtree(cookie_dir)
            
            os.makedirs(cookie_dir, mode=0o700, exist_ok=True)
            
            # Check if cookies exist (might bypass 2FA if still valid)
            cookie_exists = os.path.exists(cookie_dir) and any(
                os.path.isfile(os.path.join(cookie_dir, f))
                for f in os.listdir(cookie_dir) if f.endswith(('.cookie', '.json'))
            )
            if cookie_exists:
                logger.info("Found existing authentication cookies - attempting to use cached session")
                logger.debug("If cookies are expired or invalid, will fall back to fresh authentication")
            
            # Log authentication attempt (without password)
            logger.info(f"Attempting to authenticate with Apple ID: {self.apple_id}")
            logger.debug(f"Using cookie directory: {cookie_dir}")
            
            # Ensure password is not None and is a string
            if not isinstance(self.password, str):
                raise ValueError(f"Password must be a string, got {type(self.password)}")
            if len(self.password) == 0:
                raise ValueError("Password cannot be empty")
            
            # Log password length for debugging (but not the actual password)
            logger.debug(f"Password length: {len(self.password)} characters")
            
            # CRITICAL: Patch pyicloud BEFORE creating any instances
            # The patches must be applied at the class level before PyiCloudService.__init__ is called
            needs_2fa = False
            manual_service_creation = False
            original_srp_authentication = None
            original_authenticate = None
            original_authenticate_with_token = None
            
            # Import and patch BEFORE creating instance
            from pyicloud.base import PyiCloudService as BasePyiCloudService
            
            # Apply patches at class level (must happen before instance creation)
            try:
                
                # First, patch _authenticate_with_token to set a flag when 2FA is required
                if hasattr(BasePyiCloudService, '_authenticate_with_token'):
                    original_authenticate_with_token = BasePyiCloudService._authenticate_with_token
                    
                    def patched_authenticate_with_token(self_patched):
                        """Patched _authenticate_with_token that sets flag when 2FA is required."""
                        try:
                            return original_authenticate_with_token(self_patched)
                        except PyiCloud2FARequiredException as e:
                            # Set flag on instance so _srp_authentication knows not to try SRP
                            self_patched._2fa_required_flag = True
                            self_patched._2fa_exception = e
                            self_patched._requires_2fa = True
                            logger.info("2FA required - flag set in _authenticate_with_token")
                            raise
                    
                    BasePyiCloudService._authenticate_with_token = patched_authenticate_with_token
                    logger.info("✓ Patched pyicloud _authenticate_with_token method")
                
                # Patch _srp_authentication to check flag and raise 2FA exception instead
                if hasattr(BasePyiCloudService, '_srp_authentication'):
                    original_srp_authentication = BasePyiCloudService._srp_authentication
                    
                    def patched_srp_authentication(self_patched, headers):
                        """Patched _srp_authentication that prevents SRP when 2FA flag is set."""
                        # Check if 2FA flag is set on this instance
                        if hasattr(self_patched, '_2fa_required_flag') and self_patched._2fa_required_flag:
                            logger.info("2FA required - preventing SRP authentication, raising 2FA exception")
                            # Get the stored exception or create a new one
                            if hasattr(self_patched, '_2fa_exception') and self_patched._2fa_exception:
                                exc = self_patched._2fa_exception
                                self_patched._2fa_exception = None
                                self_patched._2fa_required_flag = False
                                raise exc
                            else:
                                # Create a new 2FA exception
                                raise PyiCloud2FARequiredException(
                                    getattr(self_patched, 'account_name', 'unknown'),
                                    None
                                )
                        # Otherwise, call the original method
                        return original_srp_authentication(self_patched, headers)
                    
                    BasePyiCloudService._srp_authentication = patched_srp_authentication
                    logger.info("✓ Patched pyicloud _srp_authentication method")
                
                # Also patch _authenticate to ensure flag propagation
                original_authenticate = BasePyiCloudService._authenticate
                
                def patched_authenticate(self_patched):
                    """Patched _authenticate that allows 2FA exceptions to propagate."""
                    try:
                        return original_authenticate(self_patched)
                    except PyiCloud2FARequiredException as e:
                        # Ensure flag is set
                        self_patched._2fa_required_flag = True
                        self_patched._2fa_exception = e
                        self_patched._requires_2fa = True
                        logger.info("2FA required - caught in _authenticate, ensuring flag is set")
                        raise
                    except PyiCloudFailedLoginException as e:
                        # Check exception chain for 2FA
                        # Also check for 403 errors which often indicate 2FA
                        from pyicloud.exceptions import PyiCloudAPIResponseException
                        is_2fa_error = False
                        
                        if hasattr(e, '__cause__') and e.__cause__:
                            cause = e.__cause__
                            while cause:
                                if isinstance(cause, PyiCloud2FARequiredException):
                                    is_2fa_error = True
                                    self_patched._2fa_required_flag = True
                                    self_patched._2fa_exception = cause
                                    self_patched._requires_2fa = True
                                    logger.info("2FA required - found in exception chain")
                                    raise cause
                                # Check for 403 API errors (often indicate 2FA)
                                if isinstance(cause, PyiCloudAPIResponseException):
                                    if hasattr(cause, 'code') and cause.code == 403:
                                        logger.info("Detected 403 error - treating as 2FA requirement")
                                        is_2fa_error = True
                                        # Create a 2FA exception
                                        two_fa_exc = PyiCloud2FARequiredException(
                                            getattr(self_patched, 'account_name', 'unknown'),
                                            None
                                        )
                                        self_patched._2fa_required_flag = True
                                        self_patched._2fa_exception = two_fa_exc
                                        self_patched._requires_2fa = True
                                        raise two_fa_exc
                                cause = getattr(cause, '__cause__', None)
                        
                        # If we didn't find 2FA in the chain but got a 403, still treat as 2FA
                        if not is_2fa_error:
                            import traceback
                            tb_str = ''.join(traceback.format_exception(type(e), e, e.__traceback__))
                            if "403" in tb_str and ("HSA2" in tb_str or "2FA" in str(e).upper()):
                                logger.info("Detected 403 with 2FA indicators - treating as 2FA")
                                two_fa_exc = PyiCloud2FARequiredException(
                                    getattr(self_patched, 'account_name', 'unknown'),
                                    None
                                )
                                self_patched._2fa_required_flag = True
                                self_patched._2fa_exception = two_fa_exc
                                self_patched._requires_2fa = True
                                raise two_fa_exc
                        
                        raise
                
                BasePyiCloudService._authenticate = patched_authenticate
                logger.info("✓ Patched pyicloud _authenticate method")
                logger.info("All patches applied successfully - ready to create PyiCloudService instance")
            except Exception as e:
                logger.warning(f"Could not patch pyicloud: {e}")
                import traceback
                logger.debug(traceback.format_exc())
            
            # Try to create the service and handle exceptions
            service_created = False
            try:
                # Try creating the service - this will raise PyiCloud2FARequiredException if 2FA is needed
                self.api = PyiCloudService(self.apple_id, self.password, cookie_directory=cookie_dir)
                service_created = True
                # If we get here, authentication succeeded (no 2FA or 2FA was handled)
                # Check if 2FA is still required (some pyicloud versions allow this)
                if hasattr(self.api, 'requires_2fa') and self.api.requires_2fa:
                    needs_2fa = True
                    logger.info("2FA authentication required (detected via requires_2fa property)")
                    # Force initialization of authentication object by accessing it
                    try:
                        if hasattr(self.api, 'authentication'):
                            auth = self.api.authentication
                            logger.info(f"Authentication object exists: {auth is not None}")
                            if auth:
                                logger.info(f"Authentication object type: {type(auth)}")
                                # Try to access trusted_devices through authentication
                                if hasattr(auth, 'trusted_devices'):
                                    devices = auth.trusted_devices
                                    logger.info(f"Found {len(devices) if devices else 0} devices via auth.trusted_devices")
                    except Exception as auth_check:
                        logger.debug(f"Error checking authentication object: {auth_check}")
            except PyiCloud2FARequiredException as e:
                # Great! We caught the 2FA exception before pyicloud's internal handler
                logger.info("Caught PyiCloud2FARequiredException - 2FA is required")
                needs_2fa = True
                # The exception might contain the service object with trusted devices
                # Check if the exception has a response with trusted devices
                if hasattr(e, 'response') and e.response:
                    logger.info("Found response in 2FA exception, checking for trusted devices...")
                    try:
                        if isinstance(e.response, dict) and 'trustedDevices' in e.response:
                            logger.info(f"Found trusted devices in exception response: {len(e.response['trustedDevices'])} devices")
                    except Exception as resp_err:
                        logger.debug(f"Error checking exception response: {resp_err}")
                
                # Try to use the service object from the exception if available
                # Otherwise create manually
                if hasattr(e, 'service') and e.service:
                    logger.info("Using service object from exception")
                    self.api = e.service
                    service_created = True
                    manual_service_creation = False
                else:
                    # Create service object manually for 2FA handling
                    self.api = PyiCloudService.__new__(PyiCloudService)
                    self.api.account_name = self.apple_id
                    self.api.password = self.password
                    self.api.cookie_directory = cookie_dir
                    # Manually set up session
                    from pyicloud.session import PyiCloudSession
                    self.api.session = PyiCloudSession(self.apple_id, self.password, cookie_directory=cookie_dir)
                    # Set requires_2fa flag
                    self.api._requires_2fa = True
                    self.api.requires_2fa = True
                    logger.info("Created PyiCloudService object for 2FA handling")
                    service_created = True
                    manual_service_creation = True
            except PyiCloudFailedLoginException as e:
                # This might be a 2FA issue wrapped in a login exception
                # Check if it's actually 2FA by examining the exception chain
                is_2fa = False
                error_msg = str(e)
                
                # Check if the error message indicates 2FA
                if "HSA2" in error_msg or "2FA" in error_msg.lower():
                    is_2fa = True
                    logger.info("Detected 2FA from error message")
                
                # Check exception chain for 2FA exception
                if not is_2fa and hasattr(e, '__cause__') and e.__cause__:
                    cause = e.__cause__
                    depth = 0
                    while cause and depth < 5:
                        if isinstance(cause, PyiCloud2FARequiredException):
                            is_2fa = True
                            logger.info(f"Found PyiCloud2FARequiredException in exception chain (depth {depth})")
                            break
                        # Check if cause is PyiCloudAPIResponseException with 403 (often indicates 2FA)
                        from pyicloud.exceptions import PyiCloudAPIResponseException
                        if isinstance(cause, PyiCloudAPIResponseException):
                            # 403 errors often indicate 2FA is required
                            if hasattr(cause, 'code') and cause.code == 403:
                                logger.info(f"Found 403 error in exception chain (depth {depth}) - likely 2FA")
                                is_2fa = True
                                break
                        cause = getattr(cause, '__cause__', None)
                        depth += 1
                
                # Also check traceback for 2FA indicators
                if not is_2fa:
                    import traceback
                    tb_str = traceback.format_exc()
                    if ("PyiCloud2FARequiredException" in tb_str or "HSA2" in tb_str or 
                        "2FA authentication required" in tb_str or "(HSA2)" in tb_str or
                        "403" in tb_str):  # 403 often indicates 2FA
                        is_2fa = True
                        logger.info("Detected 2FA from traceback (403 or HSA2 indicators)")
                
                if is_2fa:
                    logger.info("Detected 2FA requirement from PyiCloudFailedLoginException")
                    needs_2fa = True
                    # Create service object manually for 2FA handling
                    self.api = PyiCloudService.__new__(PyiCloudService)
                    self.api.account_name = self.apple_id
                    self.api.password = self.password
                    self.api.cookie_directory = cookie_dir
                    # Manually set up session
                    from pyicloud.session import PyiCloudSession
                    self.api.session = PyiCloudSession(self.apple_id, self.password, cookie_directory=cookie_dir)
                    # Set requires_2fa flag
                    self.api._requires_2fa = True
                    self.api.requires_2fa = True
                    logger.info("Created PyiCloudService object for 2FA handling")
                    service_created = True
                    manual_service_creation = True
                else:
                    # Not a 2FA issue - re-raise
                    raise
            
            # Restore original methods after service creation attempt
            try:
                from pyicloud.base import PyiCloudService as BasePyiCloudService
                if original_authenticate:
                    BasePyiCloudService._authenticate = original_authenticate
                if original_srp_authentication:
                    BasePyiCloudService._srp_authentication = original_srp_authentication
                if original_authenticate_with_token:
                    BasePyiCloudService._authenticate_with_token = original_authenticate_with_token
            except:
                pass
            
            # Ensure API object exists
            if not service_created or not hasattr(self, 'api') or self.api is None:
                # If we get here and haven't set needs_2fa, it's a real error
                raise Exception("Failed to create iCloud API object")
            
            # Handle 2FA if required
            # Check requires_2fa property or if we detected 2FA during initialization
            logger.info(f"Checking 2FA status: needs_2fa={needs_2fa}, has_api={hasattr(self, 'api')}, api_requires_2fa={hasattr(self.api, 'requires_2fa') and self.api.requires_2fa if hasattr(self, 'api') else 'N/A'}")
            if needs_2fa or (hasattr(self.api, 'requires_2fa') and self.api.requires_2fa):
                logger.info("=" * 60)
                logger.info("Two-factor authentication required - entering 2FA handling section")
                logger.info("=" * 60)
                
                # If we manually created the service, we need to trigger authentication
                # to populate trusted devices. This will fail with 2FA, but devices will be populated.
                if manual_service_creation:
                    logger.info("Triggering authentication to populate trusted devices...")
                    try:
                        # Try to authenticate - this will fail with 2FA but populate devices
                        self.api._authenticate()
                    except (PyiCloud2FARequiredException, PyiCloudFailedLoginException) as auth_ex:
                        logger.info(f"Authentication triggered (expected to fail): {type(auth_ex).__name__}")
                        # Devices should now be populated
                    except Exception as auth_ex:
                        logger.debug(f"Authentication attempt raised: {type(auth_ex).__name__}: {auth_ex}")
                        # Continue anyway - devices might still be populated
                
                # Ensure authentication object is initialized (needed for trusted_devices)
                # When service is created successfully, authentication object should exist
                logger.info("Checking authentication object...")
                if hasattr(self.api, 'authentication') and self.api.authentication:
                    logger.info("Authentication object exists, checking for trusted devices...")
                    # Try to access trusted devices through authentication object
                    try:
                        # Check if authentication has a data attribute with trusted devices
                        if hasattr(self.api.authentication, 'data') and self.api.authentication.data:
                            auth_data = self.api.authentication.data
                            logger.info(f"Authentication data keys: {list(auth_data.keys()) if isinstance(auth_data, dict) else 'not a dict'}")
                            if isinstance(auth_data, dict) and 'trustedDevices' in auth_data:
                                logger.info(f"Found trustedDevices in authentication.data: {len(auth_data['trustedDevices'])} devices")
                    except Exception as e:
                        logger.debug(f"Error checking authentication.data: {e}")
                    
                    # Try to call _get_trusted_devices if it exists
                    try:
                        if hasattr(self.api.authentication, '_get_trusted_devices'):
                            devices_from_auth = self.api.authentication._get_trusted_devices()
                            logger.info(f"Got devices from _get_trusted_devices: {len(devices_from_auth) if devices_from_auth else 0}")
                    except Exception as e:
                        logger.debug(f"Error calling _get_trusted_devices: {e}")
                else:
                    logger.warning("Authentication object not found, trying to initialize...")
                    try:
                        # Try to access requires_2fa which should trigger authentication object creation
                        _ = self.api.requires_2fa
                        # Give it a moment to initialize
                        import time
                        time.sleep(1.0)
                        
                        # Check again after accessing requires_2fa
                        if hasattr(self.api, 'authentication') and self.api.authentication:
                            logger.info("Authentication object now exists after requires_2fa access")
                        else:
                            logger.warning("Authentication object still not found after requires_2fa access")
                            # Try to inspect the service object's internal state
                            logger.info(f"Service object attributes: {[a for a in dir(self.api) if not a.startswith('__')][:20]}")
                            # Check if there's a _authentication private attribute
                            if hasattr(self.api, '_authentication'):
                                logger.info("Found _authentication private attribute")
                                self.api.authentication = self.api._authentication
                    except Exception as e:
                        logger.debug(f"Error initializing authentication: {e}")
                
                # Give the API a moment to populate trusted devices
                import time
                time.sleep(1.0)
                
                # Try to force refresh trusted devices by accessing the property multiple times
                try:
                    # Accessing requires_2fa sometimes triggers device population
                    _ = self.api.requires_2fa
                    time.sleep(0.5)
                    # Try accessing trusted_devices property directly
                    _ = self.api.trusted_devices
                    time.sleep(0.5)
                except Exception as e:
                    logger.debug(f"Error refreshing devices: {e}")
                
                if self.trusted_device_id:
                    # Use trusted device
                    devices = self.api.trusted_devices
                    
                    # Ensure devices is a list
                    if devices is None:
                        devices = []
                    elif not isinstance(devices, list):
                        devices = list(devices) if hasattr(devices, '__iter__') else []
                    
                    if len(devices) == 0:
                        raise Exception("No trusted devices found. Please set up trusted devices in your Apple ID settings.")
                    
                    try:
                        device_idx = int(self.trusted_device_id)
                        if device_idx < 0 or device_idx >= len(devices):
                            raise Exception(f"Invalid trusted_device_id: {self.trusted_device_id}. Valid range: 0-{len(devices)-1}")
                        device = devices[device_idx]
                    except ValueError:
                        raise Exception(f"Invalid trusted_device_id format: {self.trusted_device_id}. Must be a number.")
                    
                    device_name = device.get('deviceName', 'Unknown')
                    logger.info(f"Using trusted device: {device_name}")
                    if not self.api.send_verification_code(device):
                        raise Exception("Failed to send verification code")
                    logger.info(f"Verification code sent to {device_name}")
                else:
                    # List available devices
                    # Try multiple ways to access trusted devices
                    devices = None
                    
                    # Method 1: Direct property access
                    try:
                        devices = self.api.trusted_devices
                        logger.info(f"Method 1 - Direct property: got {type(devices)}, value: {devices}")
                        if devices is not None:
                            logger.info(f"  Length: {len(devices) if hasattr(devices, '__len__') else 'N/A'}")
                    except Exception as e:
                        logger.warning(f"Method 1 failed: {e}")
                    
                    # Method 1b: Check authentication object's internal data
                    if not devices or (hasattr(devices, '__len__') and len(devices) == 0):
                        try:
                            # First, ensure authentication object exists
                            if not hasattr(self.api, 'authentication') or not self.api.authentication:
                                # Try to get it from private attribute
                                if hasattr(self.api, '_authentication'):
                                    self.api.authentication = self.api._authentication
                                    logger.info("Retrieved authentication from _authentication")
                            
                            if hasattr(self.api, 'authentication') and self.api.authentication:
                                # Check all possible attributes of authentication object
                                auth_obj = self.api.authentication
                                logger.info(f"Method 1b - Authentication object type: {type(auth_obj)}")
                                auth_attrs = [a for a in dir(auth_obj) if not a.startswith('__')]
                                logger.info(f"Method 1b - Authentication object attributes (first 15): {auth_attrs[:15]}")
                                
                                # Try accessing data directly
                                if hasattr(auth_obj, 'data'):
                                    auth_data = auth_obj.data
                                    logger.info(f"Method 1b - Authentication.data type: {type(auth_data)}")
                                    if isinstance(auth_data, dict):
                                        logger.info(f"Method 1b - Authentication.data keys: {list(auth_data.keys())}")
                                        if 'trustedDevices' in auth_data:
                                            devices = auth_data['trustedDevices']
                                            logger.info(f"Method 1b - Found {len(devices)} devices in authentication.data")
                                        elif 'trusted_devices' in auth_data:
                                            devices = auth_data['trusted_devices']
                                            logger.info(f"Method 1b - Found {len(devices)} devices in authentication.data (snake_case)")
                                
                                # Try accessing via _data if it exists
                                if (not devices or (hasattr(devices, '__len__') and len(devices) == 0)) and hasattr(auth_obj, '_data'):
                                    auth_data = auth_obj._data
                                    logger.info(f"Method 1c - Checking _data, type: {type(auth_data)}")
                                    if isinstance(auth_data, dict):
                                        logger.info(f"Method 1c - _data keys: {list(auth_data.keys())}")
                                        if 'trustedDevices' in auth_data:
                                            devices = auth_data['trustedDevices']
                                            logger.info(f"Method 1c - Found {len(devices)} devices in authentication._data")
                                
                                # Try accessing trusted_devices property directly on auth object
                                if (not devices or (hasattr(devices, '__len__') and len(devices) == 0)) and hasattr(auth_obj, 'trusted_devices'):
                                    try:
                                        devices = auth_obj.trusted_devices
                                        logger.info(f"Method 1d - Found {len(devices) if devices else 0} devices via auth.trusted_devices")
                                    except Exception as e:
                                        logger.debug(f"Method 1d failed: {e}")
                        except Exception as e:
                            logger.warning(f"Method 1b failed: {e}")
                            import traceback
                            logger.debug(traceback.format_exc())
                    
                    # Method 2: Try accessing as private attribute
                    if not devices or (hasattr(devices, '__len__') and len(devices) == 0):
                        try:
                            if hasattr(self.api, '_trusted_devices'):
                                devices = self.api._trusted_devices
                                logger.info(f"Method 2 - Private attribute: got {type(devices)}")
                        except Exception as e:
                            logger.debug(f"Method 2 failed: {e}")
                    
                    # Method 3: Try calling as method if it exists
                    if not devices or (hasattr(devices, '__len__') and len(devices) == 0):
                        try:
                            if hasattr(self.api, 'get_trusted_devices') and callable(self.api.get_trusted_devices):
                                devices = self.api.get_trusted_devices()
                                logger.info(f"Method 3 - Method call: got {type(devices)}")
                        except Exception as e:
                            logger.debug(f"Method 3 failed: {e}")
                    
                    # Method 4: Try accessing via authentication object
                    if not devices or (hasattr(devices, '__len__') and len(devices) == 0):
                        try:
                            if hasattr(self.api, 'authentication') and self.api.authentication:
                                if hasattr(self.api.authentication, 'trusted_devices'):
                                    devices = self.api.authentication.trusted_devices
                                    logger.info(f"Method 4 - Via authentication: got {type(devices)}")
                                # Also try accessing via data property
                                elif hasattr(self.api.authentication, 'data') and self.api.authentication.data:
                                    auth_data = self.api.authentication.data
                                    if 'trustedDevices' in auth_data:
                                        devices = auth_data['trustedDevices']
                                        logger.info(f"Method 4b - Via authentication.data: got {type(devices)}")
                        except Exception as e:
                            logger.debug(f"Method 4 failed: {e}")
                    
                    # Method 5: Force refresh by accessing requires_2fa again
                    if not devices or (hasattr(devices, '__len__') and len(devices) == 0):
                        try:
                            # Sometimes accessing requires_2fa triggers device population
                            _ = self.api.requires_2fa
                            time.sleep(0.5)  # Give it a moment
                            devices = self.api.trusted_devices
                            logger.info(f"Method 5 - After refresh: got {type(devices)}")
                        except Exception as e:
                            logger.debug(f"Method 5 failed: {e}")
                    
                    # Method 6: Try to explicitly fetch trusted devices via authentication API
                    if not devices or (hasattr(devices, '__len__') and len(devices) == 0):
                        try:
                            if hasattr(self.api, 'authentication') and self.api.authentication:
                                # Try calling _get_trusted_devices if it exists
                                if hasattr(self.api.authentication, '_get_trusted_devices'):
                                    devices = self.api.authentication._get_trusted_devices()
                                    logger.info(f"Method 6 - Via _get_trusted_devices: got {type(devices)}")
                                # Try accessing the session and making a direct API call
                                elif hasattr(self.api, 'session') and self.api.session:
                                    # Access requires_2fa which should trigger the API call
                                    _ = self.api.requires_2fa
                                    time.sleep(1.0)  # Give more time for API call
                                    devices = self.api.trusted_devices
                                    logger.info(f"Method 6b - After session access: got {type(devices)}")
                        except Exception as e:
                            logger.debug(f"Method 6 failed: {e}")
                    
                    # Ensure devices is a list
                    if devices is None:
                        devices = []
                    elif not isinstance(devices, list):
                        try:
                            # Try to convert to list
                            if hasattr(devices, '__iter__'):
                                devices = list(devices)
                                logger.info(f"Converted to list, length: {len(devices)}")
                            else:
                                devices = []
                        except (TypeError, AttributeError) as e:
                            logger.warning(f"Error converting devices to list: {e}")
                            devices = []
                    
                    # Debug: Log what we got
                    logger.info(f"Final result: Found {len(devices)} trusted device(s)")
                    if len(devices) > 0:
                        logger.info(f"Device types: {[type(d).__name__ for d in devices[:3]]}")
                        # Try to show device names
                        for i, device in enumerate(devices[:5]):  # Show first 5
                            try:
                                if isinstance(device, dict):
                                    name = device.get('deviceName', 'Unknown')
                                elif hasattr(device, 'deviceName'):
                                    name = device.deviceName
                                elif hasattr(device, 'get'):
                                    name = device.get('deviceName', 'Unknown')
                                else:
                                    name = str(device)[:50]
                                logger.info(f"  Device {i}: {name}")
                            except Exception as e:
                                logger.debug(f"  Device {i}: (error getting name: {e})")
                    
                    # Check if devices list is empty
                    if not devices or len(devices) == 0:
                        logger.error("=" * 60)
                        logger.error("No trusted devices found for 2FA")
                        logger.error("=" * 60)
                        logger.error("")
                        logger.error("Your Apple ID requires 2FA, but pyicloud cannot find trusted devices.")
                        logger.error("This can happen if:")
                        logger.error("  1. Your account doesn't have trusted devices set up")
                        logger.error("  2. pyicloud cannot access the trusted devices API")
                        logger.error("  3. Your account uses a different 2FA method")
                        logger.error("")
                        logger.error("SOLUTIONS:")
                        logger.error("")
                        logger.error("Option 1: Use the sync method (RECOMMENDED for VMs)")
                        logger.error("  This bypasses API authentication and copies files directly:")
                        logger.error("  python3 main.py --config config.yaml --use-sync")
                        logger.error("")
                        logger.error("Option 2: Set up trusted devices")
                        logger.error("  1. Go to https://appleid.apple.com")
                        logger.error("  2. Sign in with your Apple ID")
                        logger.error("  3. Go to 'Sign-In and Security' → 'Two-Factor Authentication'")
                        logger.error("  4. Make sure you have at least one trusted device")
                        logger.error("  5. Trusted devices: iPhone, iPad, Mac, or any device you've signed into")
                        logger.error("")
                        logger.error("Option 3: Use app-specific password (if supported)")
                        logger.error("  Generate at https://appleid.apple.com → App-Specific Passwords")
                        logger.error("")
                        raise Exception("No trusted devices found. Use --use-sync method or set up trusted devices at https://appleid.apple.com")
                    
                    # Convert devices to a proper list and validate structure
                    device_list = []
                    for i, device in enumerate(devices):
                        try:
                            if isinstance(device, dict):
                                device_list.append(device)
                            else:
                                # Try to convert to dict if it's an object with attributes
                                device_dict = {}
                                if hasattr(device, 'deviceName'):
                                    device_dict['deviceName'] = device.deviceName
                                if hasattr(device, 'deviceType'):
                                    device_dict['deviceType'] = device.deviceType
                                if hasattr(device, 'deviceId'):
                                    device_dict['deviceId'] = device.deviceId
                                device_list.append(device_dict if device_dict else device)
                        except Exception as e:
                            logger.warning(f"Error processing device {i}: {e}")
                            device_list.append(device)
                    
                    if len(device_list) == 0:
                        raise Exception("No valid trusted devices found. Please set up trusted devices in your Apple ID settings.")
                    
                    logger.info("Available trusted devices:")
                    for i, device in enumerate(device_list):
                        try:
                            device_name = device.get('deviceName', 'Unknown') if isinstance(device, dict) else getattr(device, 'deviceName', 'Unknown')
                            device_type = device.get('deviceType', 'Unknown') if isinstance(device, dict) else getattr(device, 'deviceType', 'Unknown')
                            logger.info(f"  {i}: {device_name} ({device_type})")
                        except Exception as e:
                            logger.warning(f"  {i}: Unknown device (error: {e})")
                    
                    # Get and validate device selection
                    device = None
                    # Check if we have a device ID from config/env (non-interactive mode)
                    if self.trusted_device_id:
                        try:
                            device_idx = int(self.trusted_device_id)
                            if 0 <= device_idx < len(device_list):
                                device = device_list[device_idx]
                                logger.info(f"Using configured device ID: {device_idx}")
                            else:
                                raise Exception(f"Invalid trusted_device_id: {self.trusted_device_id}. Valid range: 0-{len(device_list)-1}")
                        except ValueError:
                            raise Exception(f"Invalid trusted_device_id format: {self.trusted_device_id}. Must be a number.")
                    
                    # If no device selected via config, try interactive input
                    if device is None:
                        # Check if we're in a non-interactive environment
                        import sys
                        is_interactive = sys.stdin.isatty()
                        
                        if not is_interactive and not self.two_fa_code:
                            raise Exception(
                                "Non-interactive mode detected but no device ID or 2FA code provided. "
                                "Set ICLOUD_2FA_DEVICE_ID and ICLOUD_2FA_CODE environment variables, "
                                "or configure trusted_device_id in config.yaml"
                            )
                        
                        while True:
                            try:
                                device_index = input(f"Select device (enter number 0-{len(device_list)-1}): ").strip()
                                idx = int(device_index)
                                if 0 <= idx < len(device_list):
                                    device = device_list[idx]
                                    break
                                else:
                                    logger.warning(f"Invalid selection. Please enter a number between 0 and {len(device_list)-1}")
                            except ValueError:
                                logger.warning("Invalid input. Please enter a number.")
                            except (EOFError, KeyboardInterrupt) as e:
                                raise Exception(
                                    "Device selection cancelled. For non-interactive use, set ICLOUD_2FA_DEVICE_ID "
                                    f"environment variable to a device number (0-{len(device_list)-1})"
                                )
                    
                    if device is None:
                        raise Exception("No device selected")
                    
                    device_name = device.get('deviceName', 'Unknown') if isinstance(device, dict) else getattr(device, 'deviceName', 'Unknown')
                    
                    if not self.api.send_verification_code(device):
                        raise Exception("Failed to send verification code")
                    logger.info(f"✓ Verification code sent to {device_name}")
                    logger.info("=" * 60)
                    logger.info("WAITING FOR USER INPUT: Please check your device for the verification code")
                    logger.info("=" * 60)
                
                # Allow retries for 2FA code
                max_attempts = 3
                code_validated = False
                
                # Check if we have a 2FA code from config/env (non-interactive mode)
                if self.two_fa_code:
                    logger.info("Using 2FA code from environment variable/config (non-interactive mode)")
                    code = self.two_fa_code
                    if self.api.validate_verification_code(device, code):
                        logger.info("✓ Verification code accepted")
                        code_validated = True
                    else:
                        raise Exception("Invalid 2FA code provided via environment variable/config")
                
                # If no code provided, try interactive input
                if not code_validated:
                    import sys
                    is_interactive = sys.stdin.isatty()
                    
                    if not is_interactive:
                        raise Exception(
                            "Non-interactive mode detected. Set ICLOUD_2FA_CODE environment variable with the "
                            "verification code, or run interactively. Codes are sent to your trusted device."
                        )
                    
                    logger.info(f"About to prompt for 2FA code (max {max_attempts} attempts)...")
                    for attempt in range(max_attempts):
                        logger.info(f"Prompting for 2FA code (attempt {attempt + 1}/{max_attempts})...")
                        try:
                            code = input(f"Enter 2FA code (attempt {attempt + 1}/{max_attempts}): ").strip()
                        except (EOFError, KeyboardInterrupt) as e:
                            logger.error(f"Input error: {e}")
                            logger.error("=" * 60)
                            logger.error("Non-interactive mode detected!")
                            logger.error("=" * 60)
                            logger.error("")
                            logger.error("To use 2FA non-interactively on a VM:")
                            logger.error("  1. Set ICLOUD_2FA_DEVICE_ID environment variable (device number)")
                            logger.error("  2. Request a code: The code will be sent to your trusted device")
                            logger.error("  3. Set ICLOUD_2FA_CODE environment variable with the code")
                            logger.error("  4. Run the script again")
                            logger.error("")
                            logger.error("Example:")
                            logger.error("  export ICLOUD_2FA_DEVICE_ID=0")
                            logger.error("  # Request code and check your device...")
                            logger.error("  export ICLOUD_2FA_CODE=123456")
                            logger.error("  python3 main.py --config config.yaml")
                            logger.error("")
                            raise
                        # Remove any spaces or dashes from the code
                        code = code.replace(' ', '').replace('-', '')
                        
                        if self.api.validate_verification_code(device, code):
                            logger.info("✓ Verification code accepted")
                            code_validated = True
                            break
                        else:
                            if attempt < max_attempts - 1:
                                logger.warning("Invalid verification code. Please try again.")
                                logger.info("Note: Codes expire quickly. You may need to request a new code.")
                                try:
                                    retry = input("Request new code? (y/n): ").strip().lower()
                                except (EOFError, KeyboardInterrupt):
                                    raise Exception("Cannot request new code in non-interactive mode")
                                if retry == 'y':
                                    if not self.api.send_verification_code(device):
                                        raise Exception("Failed to send new verification code")
                                    logger.info("New verification code sent")
                            else:
                                raise Exception("Invalid verification code after multiple attempts")
            
            logger.info("Successfully authenticated with iCloud")
            
        except PyiCloud2FARequiredException as e:
            error_msg = str(e)
            logger.error("=" * 60)
            logger.error("2FA Authentication Required")
            logger.error("=" * 60)
            logger.error("")
            logger.error("Your Apple ID account requires two-factor authentication.")
            logger.error("")
            logger.error("Note: App-specific passwords may not work with pyicloud.")
            logger.error("You have two options:")
            logger.error("")
            logger.error("Option 1: Use regular password with 2FA")
            logger.error("  - Use your regular Apple ID password")
            logger.error("  - Set up trusted devices at https://appleid.apple.com")
            logger.error("  - The script will prompt you to select a device and enter a code")
            logger.error("")
            logger.error("Option 2: Use the sync method (bypasses API authentication)")
            logger.error("  - Run: python3 main.py --config config.yaml --use-sync")
            logger.error("  - This copies files to a Photos library directory instead")
            logger.error("")
            raise Exception(f"2FA authentication required: {error_msg}")
        except PyiCloudFailedLoginException as e:
            error_msg = str(e)
            
            # Check if this is actually a 2FA issue that wasn't caught in the initial attempt
            # This is a fallback handler in case the patches didn't work as expected
            is_2fa_issue = False
            
            # Quick check: Look for 2FA indicators in the exception message
            if "HSA2" in error_msg or "2FA" in error_msg.lower() or "two-factor" in error_msg.lower():
                is_2fa_issue = True
                logger.info("Found 2FA indicators in error message")
            
            # Check exception chain for 2FA exception
            if not is_2fa_issue and hasattr(e, '__cause__') and e.__cause__:
                cause = e.__cause__
                depth = 0
                while cause and depth < 5:  # Limit depth to avoid infinite loops
                    if isinstance(cause, PyiCloud2FARequiredException):
                        is_2fa_issue = True
                        logger.info(f"✓ Found 2FA exception in exception chain (depth {depth})")
                        break
                    cause_str = str(cause)
                    if "HSA2" in cause_str or "PyiCloud2FARequiredException" in cause_str:
                        is_2fa_issue = True
                        logger.info(f"✓ Found 2FA indicators in exception chain (depth {depth})")
                        break
                    cause = getattr(cause, '__cause__', None)
                    depth += 1
            
            # Check traceback for 2FA indicators
            if not is_2fa_issue:
                import traceback
                tb_str = traceback.format_exc()
                if ("PyiCloud2FARequiredException" in tb_str or 
                    "HSA2" in tb_str or 
                    "2FA authentication required" in tb_str or 
                    "(HSA2)" in tb_str or
                    "2FA authentication required for account" in tb_str):
                    is_2fa_issue = True
                    logger.info("Found 2FA indicators in traceback")
                    logger.info(f"Traceback preview: {tb_str[:500]}")
            
            if is_2fa_issue:
                logger.info("=" * 60)
                logger.info("2FA Authentication Detected in Fallback Handler")
                logger.info("=" * 60)
                logger.info("")
                logger.info("Detected 2FA requirement from exception traceback.")
                logger.info("Attempting to manually create service object and handle 2FA...")
                
                # Try to manually create the service object for 2FA handling
                try:
                    # Create instance without calling __init__ (which calls authenticate)
                    self.api = PyiCloudService.__new__(PyiCloudService)
                    self.api.account_name = self.apple_id
                    self.api.password = self.password
                    self.api.cookie_directory = cookie_dir
                    
                    # Create session manually  
                    from pyicloud.session import PyiCloudSession
                    self.api.session = PyiCloudSession(self.apple_id, self.password, cookie_directory=cookie_dir)
                    
                    # Initialize the service object properly
                    if not hasattr(self.api, 'data'):
                        self.api.data = {}
                    if not hasattr(self.api, 'services'):
                        self.api.services = {}
                    
                    # Try to trigger authentication to populate trusted devices
                    logger.info("Triggering authentication to populate trusted devices...")
                    try:
                        self.api._authenticate()
                        logger.info("Authentication succeeded (unexpected)")
                    except (PyiCloud2FARequiredException, PyiCloudFailedLoginException) as auth_ex:
                        logger.info(f"Authentication raised exception (expected): {type(auth_ex).__name__}")
                    
                    # Set requires_2fa flag
                    self.api._requires_2fa = True
                    self.api.requires_2fa = True
                    needs_2fa = True
                    manual_service_creation = True
                    
                    logger.info("✓ Created PyiCloudService object for 2FA handling")
                    logger.info("Continuing to 2FA device selection and code entry...")
                    # Don't raise exception - let code continue to 2FA handling section
                    
                except Exception as manual_error:
                    logger.error(f"Failed to create service object manually: {manual_error}")
                    import traceback
                    logger.error(f"Traceback: {traceback.format_exc()}")
                    logger.error("")
                    logger.error("SOLUTIONS TO TRY:")
                    logger.error("")
                    logger.error("1. Update pyicloud to the latest version:")
                    logger.error("   pip install --upgrade pyicloud")
                    logger.error("")
                    logger.error("2. Use the sync method instead:")
                    logger.error("   python3 main.py --config config.yaml --use-sync")
                    logger.error("")
                    raise Exception(f"2FA authentication required but could not create service object. Error: {manual_error}")
            else:
                # Normal error handling for non-2FA cases
                logger.error(f"iCloud login failed: {error_msg}")
                logger.error("Possible causes:")
                logger.error("  1. Incorrect Apple ID or password")
                logger.error("  2. Account locked or requires verification")
                logger.error("  3. 2FA is enabled but not properly configured")
                logger.error("  4. Network connectivity issues")
                logger.error("  5. Stale authentication cookies")
                logger.error("  6. App-specific password not supported (try regular password)")
                logger.error("")
                logger.error("Troubleshooting steps:")
                logger.error("  - Verify your Apple ID and password are correct")
                logger.error("  - Try logging into icloud.com in a browser to verify credentials")
                logger.error("  - If using app-specific password, try your regular password instead")
                logger.error("  - Check if your account requires 2FA setup")
                logger.error("  - Ensure you have trusted devices set up at https://appleid.apple.com")
                cookie_dir = os.path.expanduser("~/.pyicloud")
                logger.error(f"  - If issues persist, try clearing cached cookies: rm -rf {cookie_dir}")
                raise Exception(f"Failed to login to iCloud: {error_msg}")
        
        # If 2FA was detected in exception handler, handle it now
        # This code runs AFTER the try/except block
        if needs_2fa and hasattr(self, 'api') and self.api is not None:
            logger.info("2FA was detected in exception handler - proceeding to 2FA handling section")
            # Trigger authentication to populate trusted devices if needed
            if manual_service_creation:
                logger.info("Triggering authentication to populate trusted devices...")
                try:
                    self.api._authenticate()
                except (PyiCloud2FARequiredException, PyiCloudFailedLoginException) as auth_ex:
                    logger.info(f"Authentication triggered (expected to fail): {type(auth_ex).__name__}")
                import time
                time.sleep(0.5)
            
            # Now handle 2FA (device selection and code entry)
            # This code is duplicated from the main 2FA handling section
            if self.trusted_device_id:
                devices = self.api.trusted_devices
                if devices is None:
                    devices = []
                elif not isinstance(devices, list):
                    devices = list(devices) if hasattr(devices, '__iter__') else []
                
                if len(devices) == 0:
                    raise Exception("No trusted devices found. Please set up trusted devices in your Apple ID settings.")
                
                try:
                    device_idx = int(self.trusted_device_id)
                    if device_idx < 0 or device_idx >= len(devices):
                        raise Exception(f"Invalid trusted_device_id: {self.trusted_device_id}. Valid range: 0-{len(devices)-1}")
                    device = devices[device_idx]
                except ValueError:
                    raise Exception(f"Invalid trusted_device_id format: {self.trusted_device_id}. Must be a number.")
                
                device_name = device.get('deviceName', 'Unknown')
                logger.info(f"Using trusted device: {device_name}")
                if not self.api.send_verification_code(device):
                    raise Exception("Failed to send verification code")
                logger.info(f"Verification code sent to {device_name}")
            else:
                devices = self.api.trusted_devices
                if devices is None:
                    devices = []
                elif not isinstance(devices, list):
                    devices = list(devices) if hasattr(devices, '__iter__') else []
                
                if len(devices) == 0:
                    raise Exception("No trusted devices found. Please set up trusted devices in your Apple ID settings.")
                
                logger.info("Available trusted devices:")
                for i, device in enumerate(devices):
                    device_name = device.get('deviceName', 'Unknown') if isinstance(device, dict) else getattr(device, 'deviceName', 'Unknown')
                    device_type = device.get('deviceType', 'Unknown') if isinstance(device, dict) else getattr(device, 'deviceType', 'Unknown')
                    logger.info(f"  {i}: {device_name} ({device_type})")
                
                # Get device selection (with non-interactive support)
                device = None
                if self.trusted_device_id:
                    try:
                        device_idx = int(self.trusted_device_id)
                        if 0 <= device_idx < len(devices):
                            device = devices[device_idx]
                            logger.info(f"Using configured device ID: {device_idx}")
                        else:
                            raise Exception(f"Invalid trusted_device_id: {self.trusted_device_id}. Valid range: 0-{len(devices)-1}")
                    except ValueError:
                        raise Exception(f"Invalid trusted_device_id format: {self.trusted_device_id}. Must be a number.")
                
                if device is None:
                    import sys
                    is_interactive = sys.stdin.isatty()
                    if not is_interactive:
                        raise Exception(
                            "Non-interactive mode: Set ICLOUD_2FA_DEVICE_ID environment variable or trusted_device_id in config.yaml"
                        )
                    
                    while True:
                        try:
                            device_index = input(f"Select device (enter number 0-{len(devices)-1}): ").strip()
                            idx = int(device_index)
                            if 0 <= idx < len(devices):
                                device = devices[idx]
                                break
                            else:
                                logger.warning(f"Invalid selection. Please enter a number between 0 and {len(devices)-1}")
                        except ValueError:
                            logger.warning("Invalid input. Please enter a number.")
                        except (EOFError, KeyboardInterrupt):
                            raise Exception("Device selection cancelled. Set ICLOUD_2FA_DEVICE_ID for non-interactive use.")
                
                if device is None:
                    raise Exception("No device selected")
                
                device_name = device.get('deviceName', 'Unknown') if isinstance(device, dict) else getattr(device, 'deviceName', 'Unknown')
                
                if not self.api.send_verification_code(device):
                    raise Exception("Failed to send verification code")
                logger.info(f"✓ Verification code sent to {device_name}")
            
            # Prompt for 2FA code (with non-interactive support)
            code_validated = False
            if self.two_fa_code:
                logger.info("Using 2FA code from environment variable/config")
                code = self.two_fa_code
                if self.api.validate_verification_code(device, code):
                    logger.info("✓ Verification code accepted")
                    code_validated = True
                else:
                    raise Exception("Invalid 2FA code provided via environment variable/config")
            
            if not code_validated:
                max_attempts = 3
                import sys
                is_interactive = sys.stdin.isatty()
                
                if not is_interactive:
                    raise Exception(
                        "Non-interactive mode: Set ICLOUD_2FA_CODE environment variable with the verification code"
                    )
                
                for attempt in range(max_attempts):
                    try:
                        code = input(f"Enter 2FA code (attempt {attempt + 1}/{max_attempts}): ").strip()
                    except (EOFError, KeyboardInterrupt) as e:
                        logger.error(f"Input error: {e}")
                        logger.error("Set ICLOUD_2FA_CODE environment variable for non-interactive use")
                        raise
                    code = code.replace(' ', '').replace('-', '')
                    
                    if self.api.validate_verification_code(device, code):
                        logger.info("✓ Verification code accepted")
                        code_validated = True
                        break
                    else:
                        if attempt < max_attempts - 1:
                            logger.warning("Invalid verification code. Please try again.")
                            try:
                                retry = input("Request new code? (y/n): ").strip().lower()
                            except (EOFError, KeyboardInterrupt):
                                raise Exception("Cannot request new code in non-interactive mode")
                            if retry == 'y':
                                if not self.api.send_verification_code(device):
                                    raise Exception("Failed to send new verification code")
                                logger.info("New verification code sent")
                        else:
                            raise Exception("Invalid verification code after multiple attempts")
            
            logger.info("Successfully authenticated with iCloud")
            return  # Exit early since we've handled 2FA
    
    def create_album(self, album_name: str) -> bool:
        """
        Create an album in iCloud Photos.
        
        Note: pyicloud may not support album creation directly.
        This is a placeholder for future implementation.
        
        Args:
            album_name: Name of the album to create
        
        Returns:
            True if successful, False otherwise
        """
        try:
            # pyicloud doesn't have direct album creation support
            # Albums may need to be created manually or through Photos app
            logger.warning(f"Album creation not supported via API: {album_name}")
            logger.info("Albums will need to be created manually in iCloud Photos")
            return False
        except Exception as e:
            logger.error(f"Failed to create album {album_name}: {e}")
            return False
    
    def upload_photo(self, photo_path: Path) -> bool:
        """
        Upload a single photo to iCloud Photos.
        
        Args:
            photo_path: Path to photo file
        
        Returns:
            True if successful, False otherwise
        """
        try:
            # pyicloud's photo upload functionality may be limited
            # The Photos API doesn't have a public upload endpoint
            # This is a placeholder - actual implementation may require
            # using Photos app sync or alternative methods
            
            logger.warning("Direct photo upload via pyicloud may not be supported")
            logger.info(f"Would upload: {photo_path.name}")
            
            # Alternative: Use Photos library sync
            # Files would need to be copied to Photos library directory
            # which then syncs to iCloud
            
            return False
            
        except Exception as e:
            logger.error(f"Failed to upload photo {photo_path.name}: {e}")
            return False
    
    def verify_file_uploaded(self, file_path: Path) -> bool:
        """
        Verify that a file was successfully uploaded to iCloud Photos.
        
        Note: This is a placeholder as direct API upload may not be supported.
        For actual verification, you may need to query the iCloud Photos API.
        
        Args:
            file_path: Path to the original file
        
        Returns:
            True if file is verified to be uploaded, False otherwise
        """
        try:
            # Since direct API upload may not be supported, verification is limited
            # In a real implementation, you would query the iCloud Photos API
            # to check if the file exists
            
            # For now, if upload_photo returned True, we assume it's uploaded
            # This is a placeholder - actual verification would require API query
            logger.debug(f"Verification not fully supported for API uploader: {file_path.name}")
            return False
            
        except Exception as e:
            logger.debug(f"Error verifying file {file_path.name}: {e}")
            return False
    
    def upload_photos_batch(self, photo_paths: List[Path], 
                           album_name: Optional[str] = None,
                           verify_after_upload: bool = True,
                           on_verification_failure: Optional[Callable[[Path], None]] = None) -> Dict[Path, bool]:
        """
        Upload multiple photos in a batch.
        
        Args:
            photo_paths: List of photo file paths
            album_name: Optional album name to add photos to
            verify_after_upload: If True, verify each file after upload
            on_verification_failure: Optional callback function(file_path) called when verification fails
        
        Returns:
            Dictionary mapping file paths to success status
        """
        results = {}
        
        for photo_path in tqdm(photo_paths, desc=f"Uploading photos"):
            success = self.upload_photo(photo_path)
            
            # Verify upload if requested
            if success and verify_after_upload:
                verified = self.verify_file_uploaded(photo_path)
                if not verified:
                    logger.warning(f"Upload verification failed for {photo_path.name}")
                    if on_verification_failure:
                        on_verification_failure(photo_path)
                    success = False
            
            results[photo_path] = success
            
            # Rate limiting
            time.sleep(0.5)
        
        successful = sum(1 for v in results.values() if v)
        logger.info(f"Uploaded {successful}/{len(results)} photos")
        
        return results
    
    def upload_video(self, video_path: Path) -> bool:
        """
        Upload a single video to iCloud Photos.
        
        Args:
            video_path: Path to video file
        
        Returns:
            True if successful, False otherwise
        """
        # Similar to photo upload - may not be directly supported
        logger.warning(f"Video upload may not be supported: {video_path.name}")
        return False


class iCloudPhotosSyncUploader:
    """
    Alternative uploader using Photos library sync method.
    
    This approach copies files to the Photos library directory,
    which then syncs to iCloud Photos automatically.
    """
    
    def __init__(self, photos_library_path: Optional[Path] = None):
        """
        Initialize the sync-based uploader.
        
        Args:
            photos_library_path: Path to Photos library (defaults to macOS default)
        """
        if photos_library_path is None:
            # Default macOS Photos library location
            home = Path.home()
            self.photos_library_path = home / "Pictures" / "Photos Library.photoslibrary"
        else:
            self.photos_library_path = photos_library_path
        
        # Photos library structure
        self.masters_path = self.photos_library_path / "Masters"
        
        logger.info(f"Using Photos library: {self.photos_library_path}")
    
    def upload_file(self, file_path: Path, album_name: Optional[str] = None) -> bool:
        """
        Copy file to Photos library for sync.
        
        Args:
            file_path: Path to media file
            album_name: Optional album name (not directly supported)
        
        Returns:
            True if successful, False otherwise
        """
        try:
            # Create Masters directory if it doesn't exist
            self.masters_path.mkdir(parents=True, exist_ok=True)
            
            # Organize by date (year/month)
            # This helps Photos app organize files
            import shutil
            from datetime import datetime
            
            # Try to get date from file metadata
            try:
                from PIL import Image
                from PIL.ExifTags import DATETIME
                
                img = Image.open(file_path)
                exif = img._getexif()
                if exif:
                    date_str = exif.get(DATETIME)
                    if date_str:
                        dt = datetime.strptime(date_str, "%Y:%m:%d %H:%M:%S")
                        year = dt.year
                        month = dt.month
                    else:
                        year = datetime.now().year
                        month = datetime.now().month
                else:
                    year = datetime.now().year
                    month = datetime.now().month
            except:
                year = datetime.now().year
                month = datetime.now().month
            
            # Create year/month directory
            target_dir = self.masters_path / str(year) / f"{month:02d}"
            target_dir.mkdir(parents=True, exist_ok=True)
            
            # Copy file
            target_path = target_dir / file_path.name
            shutil.copy2(file_path, target_path)
            
            logger.debug(f"Copied {file_path.name} to Photos library")
            return True
            
        except Exception as e:
            logger.error(f"Failed to copy {file_path.name}: {e}")
            return False
    
    def verify_file_uploaded(self, file_path: Path) -> bool:
        """
        Verify that a file was successfully uploaded to iCloud Photos.
        
        For sync method, this checks if the file exists in the Photos library.
        
        Args:
            file_path: Path to the original file
        
        Returns:
            True if file is verified to be uploaded, False otherwise
        """
        try:
            from datetime import datetime
            
            # Try to get date from file metadata to find target location
            try:
                from PIL import Image
                from PIL.ExifTags import DATETIME
                
                img = Image.open(file_path)
                exif = img._getexif()
                if exif:
                    date_str = exif.get(DATETIME)
                    if date_str:
                        dt = datetime.strptime(date_str, "%Y:%m:%d %H:%M:%S")
                        year = dt.year
                        month = dt.month
                    else:
                        year = datetime.now().year
                        month = datetime.now().month
                else:
                    year = datetime.now().year
                    month = datetime.now().month
            except:
                year = datetime.now().year
                month = datetime.now().month
            
            # Check if file exists in Photos library
            target_dir = self.masters_path / str(year) / f"{month:02d}"
            target_path = target_dir / file_path.name
            
            if target_path.exists():
                # Also verify file size matches (basic integrity check)
                if target_path.stat().st_size == file_path.stat().st_size:
                    return True
            
            return False
            
        except Exception as e:
            logger.debug(f"Error verifying file {file_path.name}: {e}")
            return False
    
    def upload_files_batch(self, file_paths: List[Path],
                          albums: Optional[Dict[Path, str]] = None,
                          verify_after_upload: bool = True,
                          on_verification_failure: Optional[Callable[[Path], None]] = None) -> Dict[Path, bool]:
        """
        Upload multiple files in a batch.
        
        Args:
            file_paths: List of file paths
            albums: Optional mapping of files to album names
            verify_after_upload: If True, verify each file after upload
            on_verification_failure: Optional callback function(file_path) called when verification fails
        
        Returns:
            Dictionary mapping file paths to success status
        """
        results = {}
        
        for file_path in tqdm(file_paths, desc="Copying to Photos library"):
            album_name = albums.get(file_path) if albums else None
            success = self.upload_file(file_path, album_name)
            
            # Verify upload if requested
            if success and verify_after_upload:
                verified = self.verify_file_uploaded(file_path)
                if not verified:
                    logger.warning(f"Upload verification failed for {file_path.name}")
                    if on_verification_failure:
                        on_verification_failure(file_path)
                    success = False
            
            results[file_path] = success
        
        successful = sum(1 for v in results.values() if v)
        logger.info(f"Copied {successful}/{len(results)} files to Photos library")
        
        return results

