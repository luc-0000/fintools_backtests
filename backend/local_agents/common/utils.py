import json
from typing import Any, Dict
from datetime import datetime
import os


def output_results(results: Dict[str, Any], stock_code :str, output_path :Any, agent_name :str, format :str ='json'):
    current_date = datetime.now().strftime('%Y-%m-%d %H:%M:%S')
    results.update({'report_date': current_date})
    """Display or save research results."""
    output_file = str(output_path) + '/' + agent_name + '_' + stock_code + '_' + datetime.now().strftime \
        ("%H:%M") + '.' + format
    if not os.path.exists(output_path):
        os.makedirs(output_path)

    # Handle JSON output
    if format == "json":
        if output_file:
            with open(output_file, "w", encoding="utf-8") as f:
                json.dump(results, f, indent=2, ensure_ascii=False)
        else:
            print(json.dumps(results, indent=2, ensure_ascii=False))
        return

    # For text output, results are already beautifully displayed during analysis
    # Just log completion
    if not output_file:
        return
    # 示例调用
    # Save to file if requested
    with open(output_file, "w", encoding="utf-8") as f:
        f.write(f"Stock Analysis Results for {results.get('stock_code', 'Unknown')}\n")
        f.write("=" * 50 + "\n\n")
        f.write(json.dumps(results, indent=2, ensure_ascii=False))

    print(f"Results saved to {output_file}")