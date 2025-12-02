"""
Script to analyze existing EPD YAML files and document all emissions-related fields.
Scans products-data directory to find what impact and resource data is available.
"""
import yaml
import os
import json
from pathlib import Path
from collections import defaultdict

def analyze_epd_file(yaml_file_path):
    """Analyze a single EPD file for impact categories and resource data"""
    try:
        with open(yaml_file_path, 'r') as f:
            epd = yaml.safe_load(f)
    except Exception as e:
        return {'error': str(e)}
    
    analysis = {
        'file_path': str(yaml_file_path),
        'has_gwp': 'gwp' in epd and epd.get('gwp') is not None,
        'has_impacts': 'impacts' in epd and bool(epd.get('impacts')),
        'has_resource_uses': 'resource_uses' in epd and bool(epd.get('resource_uses')),
        'impacts_keys': list(epd.get('impacts', {}).keys()) if epd.get('impacts') else [],
        'resource_uses_keys': list(epd.get('resource_uses', {}).keys()) if epd.get('resource_uses') else [],
        'category': epd.get('category', {}).get('display_name', 'Unknown'),
        'country': None,
        'epd_id': epd.get('id', 'Unknown'),
        'material_id': epd.get('material_id', 'Unknown'),
        'gwp_fields': {},
        'impact_values': {},
        'resource_values': {}
    }
    
    # Extract GWP-related fields
    gwp_fields = [
        'gwp', 'gwp_per_kg', 'gwp_per_category_declared_unit',
        'best_practice', 'conservative_estimate', 'lowest_plausible_gwp',
        'uncertainty_adjusted_gwp', 'standard_deviation', 'gwp_z',
        'biogenic_embodied_carbon_z', 'stored_carbon_z'
    ]
    
    for field in gwp_fields:
        if field in epd and epd[field] is not None:
            analysis['gwp_fields'][field] = epd[field]
    
    # Extract category percentile GWP values
    category = epd.get('category', {})
    for pct in ['pct10', 'pct20', 'pct30', 'pct40', 'pct50', 'pct60', 'pct70', 'pct80', 'pct90']:
        field = f'{pct}_gwp'
        if field in category:
            analysis['gwp_fields'][f'category_{field}'] = category[field]
    
    # Extract impact values if present
    if analysis['has_impacts']:
        analysis['impact_values'] = epd.get('impacts', {})
    
    # Extract resource use values if present
    if analysis['has_resource_uses']:
        analysis['resource_values'] = epd.get('resource_uses', {})
    
    # Determine country from file path
    path_parts = Path(yaml_file_path).parts
    for part in path_parts:
        if part == 'US':
            analysis['country'] = 'US'
            break
        elif part in ['IN', 'GB', 'DE', 'NL', 'CA', 'MX', 'CN']:
            analysis['country'] = part
            break
    
    return analysis

def scan_all_epds(max_files=None):
    """Scan all EPD files to find which have impact/resource data"""
    base_path = Path("../../products-data")
    
    stats = {
        'total_epds': 0,
        'with_gwp': 0,
        'with_impacts': 0,
        'with_resource_uses': 0,
        'impact_categories_found': defaultdict(int),
        'resource_types_found': defaultdict(int),
        'by_country': defaultdict(lambda: {'total': 0, 'with_gwp': 0, 'with_impacts': 0, 'with_resources': 0}),
        'by_category': defaultdict(lambda: {'total': 0, 'with_gwp': 0, 'with_impacts': 0, 'with_resources': 0}),
        'gwp_fields_found': defaultdict(int),
        'sample_epds_with_impacts': [],
        'sample_epds_with_resources': []
    }
    
    # Scan all YAML files
    yaml_files = list(base_path.rglob("*.yaml"))
    print(f"Found {len(yaml_files)} EPD files to analyze...")
    
    if max_files:
        yaml_files = yaml_files[:max_files]
        print(f"Limiting analysis to first {max_files} files for initial scan...")
    
    for yaml_file in yaml_files:
        try:
            analysis = analyze_epd_file(yaml_file)
            
            if 'error' in analysis:
                continue
            
            stats['total_epds'] += 1
            
            if analysis['has_gwp']:
                stats['with_gwp'] += 1
                for field in analysis['gwp_fields'].keys():
                    stats['gwp_fields_found'][field] += 1
            
            if analysis['has_impacts']:
                stats['with_impacts'] += 1
                for key in analysis['impacts_keys']:
                    stats['impact_categories_found'][key] += 1
                # Save sample EPDs with impacts
                if len(stats['sample_epds_with_impacts']) < 5:
                    stats['sample_epds_with_impacts'].append({
                        'file': str(yaml_file),
                        'epd_id': analysis['epd_id'],
                        'category': analysis['category'],
                        'impacts': analysis['impact_values']
                    })
            
            if analysis['has_resource_uses']:
                stats['with_resource_uses'] += 1
                for key in analysis['resource_uses_keys']:
                    stats['resource_types_found'][key] += 1
                # Save sample EPDs with resources
                if len(stats['sample_epds_with_resources']) < 5:
                    stats['sample_epds_with_resources'].append({
                        'file': str(yaml_file),
                        'epd_id': analysis['epd_id'],
                        'category': analysis['category'],
                        'resource_uses': analysis['resource_values']
                    })
            
            if analysis['country']:
                stats['by_country'][analysis['country']]['total'] += 1
                if analysis['has_gwp']:
                    stats['by_country'][analysis['country']]['with_gwp'] += 1
                if analysis['has_impacts']:
                    stats['by_country'][analysis['country']]['with_impacts'] += 1
                if analysis['has_resource_uses']:
                    stats['by_country'][analysis['country']]['with_resources'] += 1
            
            stats['by_category'][analysis['category']]['total'] += 1
            if analysis['has_gwp']:
                stats['by_category'][analysis['category']]['with_gwp'] += 1
            if analysis['has_impacts']:
                stats['by_category'][analysis['category']]['with_impacts'] += 1
            if analysis['has_resource_uses']:
                stats['by_category'][analysis['category']]['with_resources'] += 1
                
        except Exception as e:
            print(f"Error analyzing {yaml_file}: {e}")
    
    return stats

def print_report(stats):
    """Print analysis report"""
    print("\n" + "="*70)
    print("EPD Impact Categories & Resource Use Analysis Report")
    print("="*70)
    
    print(f"\nTotal EPDs analyzed: {stats['total_epds']}")
    if stats['total_epds'] > 0:
        print(f"EPDs with GWP data: {stats['with_gwp']} ({stats['with_gwp']/stats['total_epds']*100:.1f}%)")
        print(f"EPDs with other impact categories: {stats['with_impacts']} ({stats['with_impacts']/stats['total_epds']*100:.1f}%)")
        print(f"EPDs with resource use data: {stats['with_resource_uses']} ({stats['with_resource_uses']/stats['total_epds']*100:.1f}%)")
    
    print("\n" + "-"*70)
    print("GWP Fields Found:")
    print("-"*70)
    for field, count in sorted(stats['gwp_fields_found'].items(), key=lambda x: -x[1]):
        print(f"  - {field}: {count} EPDs ({count/stats['total_epds']*100:.1f}%)")
    
    if stats['impact_categories_found']:
        print("\n" + "-"*70)
        print("Impact Categories Found:")
        print("-"*70)
        for category, count in sorted(stats['impact_categories_found'].items(), key=lambda x: -x[1]):
            print(f"  - {category}: {count} EPDs")
    else:
        print("\n" + "-"*70)
        print("Impact Categories Found:")
        print("-"*70)
        print("  ⚠️  No other impact categories found in current data")
        print("  (All EPDs have empty 'impacts: {}' field)")
    
    if stats['resource_types_found']:
        print("\n" + "-"*70)
        print("Resource Use Types Found:")
        print("-"*70)
        for resource, count in sorted(stats['resource_types_found'].items(), key=lambda x: -x[1]):
            print(f"  - {resource}: {count} EPDs")
    else:
        print("\n" + "-"*70)
        print("Resource Use Types Found:")
        print("-"*70)
        print("  ⚠️  No resource use data found in current data")
        print("  (All EPDs have empty 'resource_uses: {}' field)")
    
    print("\n" + "-"*70)
    print("By Country:")
    print("-"*70)
    for country, data in sorted(stats['by_country'].items()):
        print(f"  {country}:")
        print(f"    Total: {data['total']} EPDs")
        print(f"    With GWP: {data['with_gwp']} ({data['with_gwp']/data['total']*100:.1f}%)" if data['total'] > 0 else "    With GWP: 0")
        print(f"    With impacts: {data['with_impacts']} ({data['with_impacts']/data['total']*100:.1f}%)" if data['total'] > 0 else "    With impacts: 0")
        print(f"    With resources: {data['with_resources']} ({data['with_resources']/data['total']*100:.1f}%)" if data['total'] > 0 else "    With resources: 0")
    
    print("\n" + "-"*70)
    print("By Category (top 15):")
    print("-"*70)
    for category, data in sorted(stats['by_category'].items(), key=lambda x: -x[1]['total'])[:15]:
        print(f"  {category}:")
        print(f"    Total: {data['total']} EPDs")
        print(f"    With GWP: {data['with_gwp']} ({data['with_gwp']/data['total']*100:.1f}%)" if data['total'] > 0 else "    With GWP: 0")
        print(f"    With impacts: {data['with_impacts']} ({data['with_impacts']/data['total']*100:.1f}%)" if data['total'] > 0 else "    With impacts: 0")
        print(f"    With resources: {data['with_resources']} ({data['with_resources']/data['total']*100:.1f}%)" if data['total'] > 0 else "    With resources: 0")
    
    if stats['sample_epds_with_impacts']:
        print("\n" + "-"*70)
        print("Sample EPDs with Impact Categories:")
        print("-"*70)
        for sample in stats['sample_epds_with_impacts']:
            print(f"\n  File: {sample['file']}")
            print(f"  EPD ID: {sample['epd_id']}")
            print(f"  Category: {sample['category']}")
            print(f"  Impacts: {json.dumps(sample['impacts'], indent=4)}")
    
    if stats['sample_epds_with_resources']:
        print("\n" + "-"*70)
        print("Sample EPDs with Resource Use Data:")
        print("-"*70)
        for sample in stats['sample_epds_with_resources']:
            print(f"\n  File: {sample['file']}")
            print(f"  EPD ID: {sample['epd_id']}")
            print(f"  Category: {sample['category']}")
            print(f"  Resource Uses: {json.dumps(sample['resource_uses'], indent=4)}")

def save_report_to_file(stats, output_file="emissions_analysis_report.txt"):
    """Save report to file"""
    import sys
    original_stdout = sys.stdout
    with open(output_file, 'w') as f:
        sys.stdout = f
        print_report(stats)
    sys.stdout = original_stdout
    print(f"\nReport saved to: {output_file}")

if __name__ == "__main__":
    print("="*70)
    print("Starting EPD Emissions Data Analysis")
    print("="*70)
    
    # Limit to first 500 files for initial scan (can be increased)
    stats = scan_all_epds(max_files=500)
    print_report(stats)
    
    # Save report to file
    save_report_to_file(stats)
    
    print("\n" + "="*70)
    print("Next Steps:")
    print("="*70)
    print("1. If impact/resource data is missing, check openEPD API")
    print("2. Compare EC3 API vs openEPD API responses")
    print("3. Determine if we need to combine data from both APIs")
    print("="*70)

