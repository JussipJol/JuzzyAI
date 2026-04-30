"""
Demonstrating Python's 'yield' operator (generators)
"""

# ===== BASIC YIELD EXAMPLE =====
def simple_generator():
    """A generator that yields values one at a time."""
    print("Starting...")
    yield 1  # First yield - pauses here
    print("After first yield")
    yield 2  # Second yield
    print("After second yield")
    yield 3  # Third yield
    print("Done!")

# Using the generator
print("=== Simple Generator ===")
gen = simple_generator()  # Creates generator object - NO code runs yet!
print(f"Generator object: {gen}")

# First next() - runs until first yield
print("\nFirst next():")
value1 = next(gen)
print(f"Got: {value1}")

# Second next() - runs until second yield
print("\nSecond next():")
value2 = next(gen)
print(f"Got: {value2}")

# Third next() - runs until third yield
print("\nThird next():")
value3 = next(gen)
print(f"Got: {value3}")

# Fourth next() - raises StopIteration (generator exhausted)
print("\nFourth next():")
try:
    value4 = next(gen)
    print(f"Got: {value4}")
except StopIteration:
    print("Generator is exhausted! (StopIteration caught)")

# ===== USING IN A FOR LOOP (RECOMMENDED) =====
print("\n=== Using in for loop (automatic StopIteration handling) ===")
def count_up_to(n):
    """Generator that yields numbers from 0 to n-1."""
    i = 0
    while i < n:
        yield i
        i += 1

print("Numbers from count_up_to(5):")
for num in count_up_to(5):
    print(num, end=' ')
print()  # Newline

# ===== WHY USE YIELD? MEMORY EFFICIENCY =====
print("\n=== Memory Efficiency Comparison ===")
def list_approach(n):
    """Returns a list - uses O(n) memory."""
    result = []
    for i in range(n):
        result.append(i * i)
    return result

def generator_approach(n):
    """Yields values one by one - uses O(1) memory."""
    for i in range(n):
        yield i * i  # Note: yield instead of return

# For large n, generator uses much less memory
LARGE_N = 1000000

# List approach - creates huge list in memory
# huge_list = list_approach(LARGE_N)  # Uncomment to see memory usage (careful!)

# Generator approach - processes one item at a time
total = 0
for square in generator_approach(LARGE_N):
    total += square
    if total > 1000000:  # Just to break early for demo
        break

print(f"Processed squares up to break point: total = {total}")

# ===== YIELD WITH SEND() (ADVANCED) =====
print("\n=== Generator with .send() ===")
def echo_generator():
    """Generator that can receive values via .send()."""
    received = yield None  # First yield - primes the generator
    while True:
        received = yield received  # Echo back what was sent

echo = echo_generator()
next(echo)  # Prime the generator (reach first yield)
print(f"Sent 'hello', got: {echo.send('hello')}")
print(f"Sent 42, got: {echo.send(42)}")
echo.close()

# ===== KEY POINTS TO REMEMBER =====
"""
1. 'yield' makes a function a generator function
2. Calling it returns a generator object (lazy - no code runs yet)
3. Code executes only when next() is called (or in for loop)
4. Each yield pauses execution and returns a value
5. Generators are exhausted after final yield (StopIteration)
6. Use for loops with generators - they handle StopIteration automatically
7. Memory efficient for large/data streams (compute values on-demand)
8. Can receive values via .send() after priming with next()
9. Never use 'return' in a generator for normal values (use yield instead)
   - 'return' in generator raises StopIteration with value (Python 3.3+)
"""

if __name__ == "__main__":
    # This block runs only when script is executed directly
    print("Run this file to see yield demonstrations!")