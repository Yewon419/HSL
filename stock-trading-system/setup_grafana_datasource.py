#!/usr/bin/env python3
import requests
import json

def create_postgres_datasource():
    """Create PostgreSQL datasource in Grafana"""
    
    grafana_url = "http://localhost:3000"
    api_url = f"{grafana_url}/api/datasources"
    
    # PostgreSQL datasource configuration
    datasource_config = {
        "name": "PostgreSQL",
        "type": "postgres",
        "url": "stock-db:5432",
        "access": "proxy",
        "user": "admin",
        "database": "stocktrading",
        "basicAuth": False,
        "isDefault": True,
        "jsonData": {
            "sslmode": "disable",
            "postgresVersion": 1300,
            "timescaledb": True
        },
        "secureJsonData": {
            "password": "admin123"
        },
        "uid": "postgres-datasource"
    }
    
    headers = {
        'Content-Type': 'application/json'
    }
    
    # Try with basic auth
    auth = ('admin', 'admin')
    
    try:
        # First, check if datasource already exists
        response = requests.get(api_url, auth=auth, timeout=10)
        
        if response.status_code == 200:
            datasources = response.json()
            postgres_ds = [ds for ds in datasources if ds.get('type') == 'postgres']
            
            if postgres_ds:
                print("PostgreSQL datasource already exists:")
                for ds in postgres_ds:
                    print(f"  - Name: {ds.get('name')}")
                    print(f"  - UID: {ds.get('uid')}")
                return True
        
        # Create new datasource
        response = requests.post(
            api_url,
            json=datasource_config,
            headers=headers,
            auth=auth,
            timeout=30
        )
        
        if response.status_code == 200:
            result = response.json()
            print("SUCCESS: PostgreSQL datasource created!")
            print(f"Datasource ID: {result.get('id', 'N/A')}")
            print(f"Datasource UID: {result.get('uid', 'N/A')}")
            return True
        else:
            print(f"ERROR: Failed to create datasource")
            print(f"Status Code: {response.status_code}")
            print(f"Response: {response.text}")
            return False
            
    except requests.exceptions.RequestException as e:
        print(f"ERROR: Request failed: {e}")
        return False

def test_datasource():
    """Test PostgreSQL connection"""
    
    grafana_url = "http://localhost:3000"
    
    # Get datasource UID first
    api_url = f"{grafana_url}/api/datasources"
    auth = ('admin', 'admin')
    
    try:
        response = requests.get(api_url, auth=auth, timeout=10)
        
        if response.status_code == 200:
            datasources = response.json()
            postgres_ds = [ds for ds in datasources if ds.get('type') == 'postgres']
            
            if postgres_ds:
                ds_uid = postgres_ds[0].get('uid')
                
                # Test datasource connection
                test_url = f"{grafana_url}/api/datasources/uid/{ds_uid}/health"
                
                test_response = requests.get(test_url, auth=auth, timeout=10)
                
                if test_response.status_code == 200:
                    result = test_response.json()
                    if result.get('status') == 'OK':
                        print("SUCCESS: PostgreSQL connection test passed!")
                        return True
                    else:
                        print(f"WARNING: Connection test failed: {result}")
                        return False
                else:
                    print(f"ERROR: Failed to test connection: {test_response.status_code}")
                    return False
        
        return False
            
    except requests.exceptions.RequestException as e:
        print(f"ERROR: Test request failed: {e}")
        return False

if __name__ == "__main__":
    print("Setting up Grafana PostgreSQL datasource...")
    
    # Create datasource
    if create_postgres_datasource():
        print("\nTesting connection...")
        test_datasource()
    
    print(f"\nAccess Grafana at: http://localhost:3000")
    print("   Username: admin")
    print("   Password: admin")