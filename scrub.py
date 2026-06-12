import os
import re

def remove_lines_with(filepath, patterns):
    with open(filepath, 'r') as f:
        lines = f.readlines()
    
    new_lines = []
    for line in lines:
        if not any(p in line.lower() for p in patterns):
            new_lines.append(line)
            
    with open(filepath, 'w') as f:
        f.writelines(new_lines)

# 1. kaicode/ui/display.py
remove_lines_with('kaicode/ui/display.py', ['claude-opus', 'claude-sonnet', 'claude-haiku', 'claude-3-5', 'claude code style', 'claude code\'s'])
# Also need to scrub "OpenAI"
remove_lines_with('kaicode/ui/display.py', ['openai'])

# 2. kaicode/pricing.py
remove_lines_with('kaicode/pricing.py', ['claude-', 'openai'])

# 3. kaicode/config.py
with open('kaicode/config.py', 'r') as f:
    config_content = f.read()

config_content = config_content.replace('"openai", ', '')
config_content = config_content.replace('"openai"', '')
config_content = re.sub(r'\s*"OPENAI_API_KEY": \("openai", "api_key"\),\n', '', config_content)

# Remove the openai provider block in default config
import ast
lines = config_content.split('\n')
new_lines = []
skip = False
for line in lines:
    if '"openai": {' in line:
        skip = True
    if skip and '},' in line and '"default_model"' not in line:
        skip = False
        continue
    if not skip:
        new_lines.append(line)

with open('kaicode/config.py', 'w') as f:
    f.write('\n'.join(new_lines))


# 4. kaicode/app.py
with open('kaicode/app.py', 'r') as f:
    app_content = f.read()

# remove fallback: "openai": "model-sonnet-4-6",
app_content = re.sub(r'\s*"openai": "claude-[^"]+",\n', '', app_content)
app_content = app_content.replace('— like KaiCode.', '')

with open('kaicode/app.py', 'w') as f:
    f.write(app_content)


# 5. kaicode/project_detector.py
with open('kaicode/project_detector.py', 'r') as f:
    pd_content = f.read()

pd_content = pd_content.replace('AGENTS.md', 'AGENTS.md')
pd_content = pd_content.replace('KaiCode', 'KaiCode')
with open('kaicode/project_detector.py', 'w') as f:
    f.write(pd_content)


# 6. kaicode/main.py
with open('kaicode/main.py', 'r') as f:
    main_content = f.read()

main_content = main_content.replace('AI-style', 'KaiCode-style')
main_content = main_content.replace('AI', 'KaiCode')
main_content = main_content.replace('AGENTS.md', 'AGENTS.md')
main_content = main_content.replace('openai/', '')
main_content = main_content.replace('openai, ', '')
main_content = main_content.replace('OpenAI, ', '')
main_content = main_content.replace('/openai', '')
main_content = main_content.replace('ollama/openai', 'ollama/openai')

with open('kaicode/main.py', 'w') as f:
    f.write(main_content)


# 7. README.md
remove_lines_with('README.md', ['openai claude', 'claude opus', 'openai_api_key', 'openai:', 'default_provider: openai'])

with open('README.md', 'r') as f:
    rm_content = f.read()

rm_content = rm_content.replace('AI-style', 'KaiCode-style')
rm_content = rm_content.replace('AI', 'KaiCode')
rm_content = rm_content.replace('openai', 'openai')
rm_content = rm_content.replace('model-sonnet-4-6', 'gpt-4o')

with open('README.md', 'w') as f:
    f.write(rm_content)

# 8. kaicode/providers/__init__.py
with open('kaicode/providers/__init__.py', 'r') as f:
    prov_content = f.read()

prov_content = re.sub(r'from kaicode\.providers\.openai import OpenAIProvider\n', '', prov_content)
prov_content = re.sub(r'\s*"OpenAIProvider",\n', '\n', prov_content)
prov_content = re.sub(r'\s*"openai": OpenAIProvider,\n', '\n', prov_content)

with open('kaicode/providers/__init__.py', 'w') as f:
    f.write(prov_content)

print("Scrub complete.")
