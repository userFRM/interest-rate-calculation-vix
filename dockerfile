# Multi-stage build for minimal image size
FROM python:3.11-slim as builder

# Set working directory
WORKDIR /app

# Copy source code
COPY src/treasury_rates.py /app/

# Test that the script runs
RUN python treasury_rates.py --help

# Final stage
FROM python:3.11-slim

# Create non-root user
RUN useradd -m -u 1000 treasury && \
    mkdir -p /data && \
    chown treasury:treasury /data

# Set working directory
WORKDIR /app

# Copy from builder
COPY --from=builder /app/treasury_rates.py /app/

# Switch to non-root user
USER treasury

# Set entrypoint
ENTRYPOINT ["python", "treasury_rates.py"]

# Default command (can be overridden)
CMD ["--help"]
