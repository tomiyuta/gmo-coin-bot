# Contributing to GMO Coin Bot

Thank you for your interest in contributing to GMO Coin Bot! This document provides guidelines for contributing to this project.

## Code of Conduct

By participating in this project, you agree to abide by our Code of Conduct. Please be respectful and inclusive in all interactions.

## How Can I Contribute?

### Reporting Bugs

Before creating bug reports, please check the existing issues to avoid duplicates. When creating a bug report, include:

- **Use a clear and descriptive title**
- **Describe the exact steps to reproduce the problem**
- **Provide specific examples to demonstrate the steps**
- **Describe the behavior you observed after following the steps**
- **Explain which behavior you expected to see instead and why**
- **Include details about your configuration and environment**

### Suggesting Enhancements

If you have a suggestion for a new feature or enhancement:

- **Use a clear and descriptive title**
- **Provide a step-by-step description of the suggested enhancement**
- **Provide specific examples to demonstrate the steps**
- **Describe the current behavior and explain which behavior you expected to see instead**

### Pull Requests

1. **Fork the repository**
2. **Create a new branch** for your feature (`git checkout -b feature/amazing-feature`)
3. **Make your changes** following the coding standards
4. **Test your changes** thoroughly
5. **Commit your changes** with clear commit messages
6. **Push to your branch** (`git push origin feature/amazing-feature`)
7. **Create a Pull Request**

## Development Setup

### Prerequisites

- Python 3.8 or higher
- Git

### Local Development

1. **Clone the repository**
   ```bash
   git clone https://github.com/yourusername/gmo-coin-bot.git
   cd gmo-coin-bot
   ```

2. **Install dependencies**
   ```bash
   pip install -r requirements.txt
   ```

3. **Create a test configuration**
   ```bash
   cp config_example.json config.json
   # Edit config.json with your test API keys
   ```

4. **Run tests** (if available)
   ```bash
   python -m pytest
   ```

## Coding Standards

### Python Code Style

- Follow [PEP 8](https://www.python.org/dev/peps/pep-0008/) style guidelines
- Use meaningful variable and function names
- Add comments for complex logic
- Keep functions small and focused

### Commit Messages

Use clear and descriptive commit messages:

```
feat: add new trading strategy
fix: resolve API connection timeout
docs: update README with new features
style: format code according to PEP 8
refactor: simplify configuration loading
test: add unit tests for risk management
```

### Code Documentation

- Add docstrings to all functions and classes
- Include type hints where appropriate
- Document complex algorithms and business logic
- Update README.md for new features

## Testing

### Before Submitting

- Test your changes with different configurations
- Verify that error handling works correctly
- Test with both valid and invalid inputs
- Ensure backward compatibility when possible

### Test Cases

When adding new features, consider testing:

- **Normal operation** with valid inputs
- **Error conditions** with invalid inputs
- **Edge cases** with boundary values
- **Performance** with large datasets
- **Security** with potentially malicious inputs

## Security Considerations

### API Keys and Secrets

- Never commit API keys or secrets to the repository
- Use environment variables for sensitive data
- Follow the principle of least privilege
- Validate all user inputs

### Data Protection

- Ensure proper error handling without exposing sensitive information
- Log security-relevant events
- Implement rate limiting where appropriate
- Validate all external data

## Review Process

1. **Automated Checks**: All PRs must pass automated checks
2. **Code Review**: At least one maintainer must approve
3. **Testing**: Changes must be tested in a staging environment
4. **Documentation**: New features must be documented

## Release Process

### Version Numbers

We follow [Semantic Versioning](https://semver.org/):

- **MAJOR** version for incompatible API changes
- **MINOR** version for backwards-compatible functionality
- **PATCH** version for backwards-compatible bug fixes

### Release Checklist

- [ ] All tests pass
- [ ] Documentation is updated
- [ ] CHANGELOG.md is updated
- [ ] Version number is updated
- [ ] Release notes are prepared

## Getting Help

If you need help with contributing:

- Check existing issues and pull requests
- Ask questions in the discussions section
- Contact maintainers for guidance

## License

By contributing to this project, you agree that your contributions will be licensed under the MIT License.

Thank you for contributing to GMO Coin Bot! 