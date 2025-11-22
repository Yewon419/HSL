#!/usr/bin/env python3
import requests
import json

def import_grafana_dashboard():
    """Import the fixed enhanced dashboard to Grafana"""
    
    # Grafana API endpoint
    grafana_url = "http://localhost:3000"
    dashboard_file = "F:/hhstock/stock-trading-system/technical_indicators_dashboard_ver2.json"
    
    # Read dashboard JSON
    with open(dashboard_file, 'r', encoding='utf-8') as f:
        dashboard_data = json.load(f)

    # Add overwrite option to update existing dashboard
    dashboard_data["overwrite"] = True
    
    # Grafana API endpoint for dashboard import
    api_url = f"{grafana_url}/api/dashboards/db"
    
    headers = {
        'Content-Type': 'application/json'
    }
    
    # Try with basic auth
    auth = ('admin', 'admin')
    
    try:
        response = requests.post(
            api_url, 
            json=dashboard_data,
            headers=headers,
            auth=auth,
            timeout=30
        )
        
        if response.status_code == 200:
            result = response.json()
            print("SUCCESS: Dashboard imported successfully!")
            print(f"Dashboard ID: {result.get('id', 'N/A')}")
            print(f"Dashboard UID: {result.get('uid', 'N/A')}")
            print(f"Dashboard URL: {grafana_url}/d/{result.get('uid', 'N/A')}")
        else:
            print(f"ERROR: Failed to import dashboard")
            print(f"Status Code: {response.status_code}")
            print(f"Response: {response.text}")
            
    except requests.exceptions.RequestException as e:
        print(f"ERROR: Request failed: {e}")

def check_postgres_connection():
    """Check if PostgreSQL datasource is configured"""
    grafana_url = "http://localhost:3000"
    api_url = f"{grafana_url}/api/datasources"
    
    auth = ('admin', 'admin')
    
    try:
        response = requests.get(api_url, auth=auth, timeout=10)
        
        if response.status_code == 200:
            datasources = response.json()
            print("Current Grafana Datasources:")
            for ds in datasources:
                print(f"  - {ds.get('name', 'Unknown')} ({ds.get('type', 'Unknown')})")
                if ds.get('type') == 'postgres':
                    print(f"    UID: {ds.get('uid')}")
                    print(f"    URL: {ds.get('url')}")
            
            postgres_ds = [ds for ds in datasources if ds.get('type') == 'postgres']
            if not postgres_ds:
                print("WARNING: No PostgreSQL datasource found!")
                return False
            else:
                print("SUCCESS: PostgreSQL datasource configured")
                return True
        else:
            print(f"ERROR: Failed to get datasources: {response.status_code}")
            return False
            
    except requests.exceptions.RequestException as e:
        print(f"ERROR: Request failed: {e}")
        return False

if __name__ == "__main__":
    print("Checking Grafana setup...")
    
    # Check datasources first
    if check_postgres_connection():
        print("\nImporting dashboard...")
        import_grafana_dashboard()
    else:
        print("ERROR: Please configure PostgreSQL datasource first")
        
    print(f"\nAccess Grafana at: http://localhost:3000")
    print("   Username: admin")
    print("   Password: admin")