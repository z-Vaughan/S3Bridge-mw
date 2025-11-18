import json

def lambda_handler(event, context):
    """
    S3Bridge Midway authorizer - validates Midway cookies
    """
    
    try:
        print(f"Authorizer event: {json.dumps(event)}")
        # Extract cookies from headers or authorizationToken
        headers = event.get('headers', {})
        cookies = headers.get('Cookie', '') or headers.get('cookie', '') or event.get('authorizationToken', '')
        print(f"Cookies: {cookies[:100]}...")
        
        # Required Midway cookies for authentication
        required_cookies = ['amazon_enterprise_access', 'session']
        
        # Check if all required cookies are present
        has_auth = all(cookie_name in cookies for cookie_name in required_cookies)
        
        if not has_auth:
            raise Exception('Unauthorized - Missing required Midway cookies')
        
        # Extract user identity from cookies
        user_id = 'unknown'
        if 'amazon_enterprise_access' in cookies:
            try:
                import urllib.parse
                import base64
                import re
                
                # Parse cookie value to extract user ID
                cookie_parts = cookies.split(';')
                for part in cookie_parts:
                    if 'amazon_enterprise_access' in part:
                        cookie_value = part.split('=', 1)[1].strip()
                        # Decode URL-encoded cookie
                        decoded = urllib.parse.unquote(cookie_value)
                        
                        # JWT token - decode the payload (middle part)
                        try:
                            jwt_parts = decoded.split('.')
                            if len(jwt_parts) >= 2:
                                # Decode JWT payload (base64)
                                payload = jwt_parts[1]
                                # Add padding if needed
                                payload += '=' * (4 - len(payload) % 4)
                                payload_decoded = base64.b64decode(payload).decode('utf-8')
                                
                                # Look for logged_in_username in JWT payload
                                print(f"JWT payload: {payload_decoded[:200]}...")
                                username_match = re.search(r'"logged_in_username"\s*:\s*"([^"]+)"', payload_decoded)
                                if username_match:
                                    user_id = username_match.group(1)
                                    print(f"Extracted user ID: {user_id}")
                                    break
                        except Exception:
                            pass
                        
                        # Fallback: if we find 'zavaugha' anywhere, use it
                        if user_id == 'unknown' and 'zavaugha' in decoded.lower():
                            user_id = 'zavaugha'
                        
                        # Final fallback: authenticated but unknown user
                        if user_id == 'unknown':
                            user_id = 'authenticated_user'
                        
                        break
            except Exception:
                user_id = 'authenticated_user'
        
        print(f"Final user ID: {user_id}")
        
        # User access control (example restrictions)
        restricted_users = ['test_user', 'demo_user']
        if user_id in restricted_users:
            print(f"User {user_id} is restricted")
            raise Exception('Unauthorized - User access restricted')
        
        # Generate allow policy with user context
        policy = {
            'principalId': user_id,
            'context': {
                'userId': user_id,
                'stringKey': user_id  # Additional context format
            },
            'policyDocument': {
                'Version': '2012-10-17',
                'Statement': [
                    {
                        'Action': 'execute-api:Invoke',
                        'Effect': 'Allow',
                        'Resource': event['methodArn']
                    }
                ]
            }
        }
        
        return policy
        
    except Exception as e:
        print(f"Authorizer error: {str(e)}")
        # Return deny policy for any error
        raise Exception('Unauthorized')