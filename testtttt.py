import os
import re
import pandas as pd
from radon.complexity import cc_visit

def clean_function_content(content, language):
    if language == 'python':
        content = re.sub(r'#.*', '', content)
        content = re.sub(r'""".*?"""', '', content, flags=re.DOTALL)
        content = re.sub(r"'''.*?'''", '', content, flags=re.DOTALL)
    else:
        content = re.sub(r'//.*', '', content)
        content = re.sub(r'/\*[\s\S]*?\*/', '', content, flags=re.DOTALL)
        content = '\n'.join(line for line in content.splitlines() if line.strip())
    return content

def extract_function_lines(content, language):
    function_lines = {}
    if language == 'python':
        functions = re.findall(r'def\s+(\w+)\s*\(', content)
        for func in functions:
            func_start = content.find(f'def {func}(')
            func_end = content.find('\ndef ', func_start + 1)
            if func_end == -1:
                func_end = len(content)
            function_content = content[func_start:func_end]
            cleaned_function_content = clean_function_content(function_content, language)
            lines = cleaned_function_content.split('\n')
            function_lines[func] = len(lines)
    elif language in ['java', 'c', 'cpp']:
        function_pattern = r'^\s*(?!else\s+if\s*\()(?:(?:static\s+)?(?:[a-zA-Z_]\w*\s+)+[a-zA-Z_]\w*\s*\([^)]*\)\s*\{|\bISR\s*\(\s*\w+\s*\))'
        functions = list(re.finditer(function_pattern, content, re.MULTILINE))
        for i, func in enumerate(functions):
            func_start = func.start()
            if i + 1 < len(functions):
                func_end = functions[i + 1].start()
            else:
                func_end = len(content)
            function_content = content[func_start:func_end]
            cleaned_function_content = clean_function_content(function_content, language)
            lines = cleaned_function_content.split('\n')
            func_signature = content[func_start:content.find('{', func_start)].strip()
            func_name_match = re.match(r'^\s*(?:static\s+)?(?:[\w\*]+\s+)+([\w\*]+)\s*\(', func_signature)
            if not func_name_match:
                func_name_match = re.match(r'\b(?:[a-zA-Z_]\w*\s+)+([a-zA-Z_]\w*)\s*\(|\bISR\s*\(\s*([a-zA-Z_]\w*)\s*\)', func_signature)
            if func_name_match:
                func_name = func_name_match.group(1) or func_name_match.group(2)
                function_lines[func_name] = len(lines)
            else:
                print(f"Warning: Could not extract function name from signature: {func_signature}")
    return function_lines

def remove_comments(content):
    content = re.sub(r'//.*', '', content)
    content = re.sub(r'/\*[\s\S]*?\*/', '', content, flags=re.DOTALL)
    return content

def count_decision_points(content):
    decision_patterns = [
        r'\bif\b', r'\belse\s*if\b', r'\bfor\b', r'\bwhile\b', r'\bcase\b', r'\bswitch\b',
        r'&&', r'\|\|', r'\?\:', r'\bdo\b', r'\bgoto\b'
    ]

    decision_points = sum(len(re.findall(pattern, content)) for pattern in decision_patterns)
    decision_points += len(re.findall(r'\[.*?for.*?in.*?\]', content))

    return decision_points

def count_function_calls(content):
    # Improved regex pattern to find function calls
    function_calls = re.findall(r'\b\w+\s*\([^{};]*\)\s*;', content)
    return len(function_calls)

def count_function_calls_per_function(content, language):
    function_calls_per_function = {}
    if language == 'python':
        functions = re.findall(r'def\s+(\w+)\s*\(', content)
        for func in functions:
            func_start = content.find(f'def {func}(')
            func_end = content.find('\ndef ', func_start + 1)
            if func_end == -1:
                func_end = len(content)
            function_content = content[func_start:func_end]
            cleaned_function_content = clean_function_content(function_content, language)
            function_calls_per_function[func] = count_function_calls(cleaned_function_content)
    elif language in ['java', 'c', 'cpp']:
        function_pattern = r'^\s*(?!else\s+if\s*\()(?:(?:static\s+)?(?:[a-zA-Z_]\w*\s+)+[a-zA-Z_]\w*\s*\([^)]*\)\s*\{|\bISR\s*\(\s*\w+\s*\))'
        functions = list(re.finditer(function_pattern, content, re.MULTILINE))
        for i, func in enumerate(functions):
            func_start = func.start()
            if i + 1 < len(functions):
                func_end = functions[i + 1].start()
            else:
                func_end = len(content)
            function_content = content[func_start:func_end]
            cleaned_function_content = clean_function_content(function_content, language)
            func_signature = content[func_start:content.find('{', func_start)].strip()
            func_name_match = re.match(r'^\s*(?:static\s+)?(?:[\w\*]+\s+)+([\w\*]+)\s*\(', func_signature)
            if not func_name_match:
                func_name_match = re.match(r'\b(?:[a-zA-Z_]\w*\s+)+([a-zA-Z_]\w*)\s*\(|\bISR\s*\(\s*([a-zA-Z_]\w*)\s*\)', func_signature)
            if func_name_match:
                func_name = func_name_match.group(1) or func_name_match.group(2)
                function_calls_per_function[func_name] = count_function_calls(cleaned_function_content)
    return function_calls_per_function

def calculate_cyclomatic_complexity(content, language):
    cyclomatic_complexities = {}

    if language == 'python':
        blocks = cc_visit(content)
        for block in blocks:
            cyclomatic_complexities[block.name] = block.complexity
    else:
        if language in ['java', 'c', 'cpp']:
            function_pattern = r'^\s*(?!else\s+if\s*\()(?:(?:static\s+)?(?:[a-zA-Z_]\w*\s+)+[a-zA-Z_]\w*\s*\([^)]*\)\s*\{|\bISR\s*\(\s*\w+\s*\))'
            functions = list(re.finditer(function_pattern, content, re.MULTILINE))

            for i, func in enumerate(functions):
                func_start = func.start()
                if i + 1 < len(functions):
                    func_end = functions[i + 1].start()
                else:
                    func_end = len(content)
                func_content = content[func_start:func_end]
                cleaned_function_content = clean_function_content(func_content, language)

                decision_points = count_decision_points(cleaned_function_content)
                cyclomatic_complexity = decision_points + 1
                func_signature = content[func_start:content.find('{', func_start)].strip()
                func_name_match = re.match(r'^\s*(?:static\s+)?(?:[\w\*]+\s+)+([\w\*]+)\s*\(', func_signature)
                if not func_name_match:
                    func_name_match = re.match(r'\b(?:[a-zA-Z_]\w*\s+)+([a-zA-Z_]\w*)\s*\(|\bISR\s*\(\s*([a-zA-Z_]\w*)\s*\)', func_signature)
                if func_name_match:
                    func_name = func_name_match.group(1) or func_name_match.group(2)
                    cyclomatic_complexities[func_name] = cyclomatic_complexity

    return cyclomatic_complexities

def estimate_hours(calls, complexity, statements):
    return 5 * calls + 4 * complexity + 3 * statements + 15

def analyze_file(filepath, language):
    try:
        with open(filepath, 'r', encoding='utf-8', errors='ignore') as file:
            content = file.read()
    except Exception as e:
        print(f"Error reading file {filepath}: {e}")
        return

    # Remove comments before processing the content
    content_no_comments = remove_comments(content)

    num_lines = len(content.splitlines())
    function_lines = extract_function_lines(content_no_comments, language)
    cyclomatic_complexities = calculate_cyclomatic_complexity(content_no_comments, language)
    function_calls_per_function = count_function_calls_per_function(content_no_comments, language)
    functions = list(function_lines.keys())

    print(f'File: {filepath}')
    print(f'Lines: {num_lines}')
    print(f'Functions: {functions}')
    print(f'Function Lines: {function_lines}')
    print(f'Cyclomatic Complexities: {cyclomatic_complexities}')
    print(f'Function Calls per Function: {function_calls_per_function}')

    return num_lines, functions, cyclomatic_complexities, function_lines, function_calls_per_function

def get_c_files_from_directory(directory):
    c_files = []
    for root, _, files in os.walk(directory):
        for file in files:
            if file.endswith('.c'):
                c_files.append(os.path.join(root, file))
    return c_files

def main(directory):
    """Main function to analyze all C files in a directory and save results to an Excel file."""
    filepaths = get_c_files_from_directory(directory)
    processed_files = {}

    data_general = {
        'File': [],
        'Language': [],
        'Lines of Code': [],
        'Number of Functions': [],
    }

    function_data = []

    for filepath in filepaths:
        filename = os.path.basename(filepath)
        if filename in processed_files:
            continue

        language = 'c'

        results = analyze_file(filepath, language)
        if not results:
            continue

        num_lines, functions, cyclomatic_complexities, function_lines, function_calls_per_function = results

        data_general['File'].append(filename)
        data_general['Language'].append(language.capitalize())
        data_general['Lines of Code'].append(num_lines)
        data_general['Number of Functions'].append(len(functions))

        for func in functions:
            complexity = cyclomatic_complexities.get(func, 'N/A')
            function_calls = function_calls_per_function.get(func, 'N/A')
            statements = function_lines.get(func, 'N/A')
            if complexity != 'N/A' and function_calls != 'N/A' and statements != 'N/A':
                estimation = estimate_hours(function_calls, complexity, statements)
                man_days = estimation / 8
                man_days_str = f"{man_days:.2f}"
            else:
                estimation = 'N/A'
                man_days_str = 'N/A'
            function_data.append({
                'File': filename,
                'Language': language.capitalize(),
                'Function Names': func,
                'Function Lines': statements,
                'Cyclomatic Complexity': complexity,
                'Estimation (hours)': estimation,
                'Man Days': man_days_str,
                'Function Calls': function_calls,
            })

        processed_files[filename] = True

    df_general = pd.DataFrame(data_general)
    df_functions = pd.DataFrame(function_data)

    output_path = r'C:\Users\2318641\Downloads\Line_check.xlsx'

    try:
        with open(output_path, 'w') as f:
            pass
    except PermissionError:
        output_path = r'C:\Users\2318641\Downloads\Line_check_alternate.xlsx'

    with pd.ExcelWriter(output_path, engine='xlsxwriter') as writer:
        df_general.to_excel(writer, sheet_name='General_Data', index=False)
        df_functions.to_excel(writer, sheet_name='Function_Details', index=False)
    print(f'Data has been written to {output_path}')

if __name__ == "__main__":
    directory_path = r"C:\Users\2318641\Downloads\Complexity_Check"
    main(directory_path)