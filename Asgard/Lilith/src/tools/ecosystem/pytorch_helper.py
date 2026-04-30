# Backend/tools/ecosystem/pytorch_helper.py
# PyTorch Model Generator Helper for Lilith
# Provides automated PyTorch model template generation

import argparse
import sys


def generate_model_code(
    model_name: str, input_size: int, hidden_size: int, output_size: int, layers: int
):
    """Generates a PyTorch model template based on parameters."""

    lines = []
    lines.append("import torch")
    lines.append("import torch.nn as nn")
    lines.append("")
    lines.append(f"class {model_name}(nn.Module):")
    lines.append(f"    def __init__(self):")
    lines.append(f"        super({model_name}, self).__init__()")
    lines.append(f"        self.flatten = nn.Flatten()")
    lines.append(f"        self.layers = nn.Sequential(")
    lines.append(f"            nn.Linear({input_size}, {hidden_size}),")
    lines.append(f"            nn.ReLU(),")

    # Generic hidden layers
    for i in range(max(0, layers - 1)):
        lines.append(f"            nn.Linear({hidden_size}, {hidden_size}),")
        lines.append(f"            nn.ReLU(),")

    lines.append(f"            nn.Linear({hidden_size}, {output_size})")
    lines.append(f"        )")
    lines.append("")
    lines.append(f"    def forward(self, x):")
    lines.append(f"        x = self.flatten(x)")
    lines.append(f"        logits = self.layers(x)")
    lines.append(f"        return logits")

    return "\n".join(lines)


def handle_pytorch_command(command_args):
    # Example usage: create_model MyModel --input_size 784 --hidden...
    parser = argparse.ArgumentParser(description="PyTorch Assistant Helper")
    subparsers = parser.add_subparsers(dest="action")

    # Create Model Command
    create_parser = subparsers.add_parser("create_model")
    create_parser.add_argument("name", type=str, help="Model class name")
    create_parser.add_argument("--input_size", type=int, default=784)
    create_parser.add_argument("--hidden_size", type=int, default=64)
    create_parser.add_argument("--output_size", type=int, default=10)
    create_parser.add_argument("--layers", type=int, default=1)

    try:
        # Split string args if passed as a single string, or use sys.argv
        if isinstance(command_args, str):
            import shlex

            args = parser.parse_args(shlex.split(command_args))
        else:
            args = parser.parse_args(command_args)

        if args.action == "create_model":
            code = generate_model_code(
                args.name,
                args.input_size,
                args.hidden_size,
                args.output_size,
                args.layers,
            )
            return f"```python\n{code}\n```"

    except SystemExit:
        return "Error parsing arguments."
    except Exception as e:
        return f"Error executing PyTorch helper: {e}"

    return "Unknown PyTorch command."


if __name__ == "__main__":
    # Test execution
    if len(sys.argv) > 1:
        print(handle_pytorch_command(sys.argv[1:]))
    else:
        # Manual debug test
        test_cmd = (
            "create_model SimpleNet --input_size 1024 --hidden_size 128 --layers 2"
        )
        print(handle_pytorch_command(test_cmd))
