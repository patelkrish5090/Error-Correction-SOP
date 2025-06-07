"""
Code written by:
    Atharva Pandit
    2023B5A70987G
"""

from qiskit import QuantumCircuit, QuantumRegister, ClassicalRegister, transpile
from qiskit_aer import AerSimulator
import warnings
warnings.filterwarnings('ignore')

class ShorCode:
    """
    Implementation of the 9-qubit Shor code for quantum error correction.
    The Shor code can correct both bit-flip (X) and phase-flip (Z) errors.
    Since Y-flips involve using both X and Z, I've omitted it from here, also I could not find it in the textbook.
    """
    
    def __init__(self):
        self.n_qubits = 9
        self.n_ancilla = 1  # For syndrome measurement, we use repeated ancilla bits due to easy of coding

    def encode(self, circuit, data_qubit=0):
        """
        Encode a single qubit into the 9-qubit Shor code.
        The encoding concatenates phase-flip and bit-flip repetition codes.
        We create a superposition state and apply C-NOT gates wherever needed, as per the circuit diagram given.
        """

        circuit.cx(data_qubit, 3)
        circuit.cx(data_qubit, 6)
        
        circuit.h(0)
        circuit.h(3)
        circuit.h(6)
        
        circuit.cx(0, 1)
        circuit.cx(0, 2)
        circuit.cx(3, 4)
        circuit.cx(3, 5)
        circuit.cx(6, 7)
        circuit.cx(6, 8)

        return circuit
    
    def add_error(self, circuit, error_type, qubit):
        """
        Add a specific error to test the error correction capability.
        error_type: 'X' for bit-flip, 'Z' for phase-flip
        """
        if error_type == 'X':
            circuit.x(qubit)
        elif error_type == 'Z':
            circuit.z(qubit)
        return circuit
        
    
    def syndrome_eigenvalue_measurement(self, circuit):
        """
        Perform syndrome measurements using stabilizer eigenvalue detection.
        More fundamental approach than parity checking, also followed in the textbook.
        """
        syndrome_reg = circuit.cregs[-1]

        # Bit-flip stabilizer measurements for each block
        # Block 1: Z₀Z₁ and Z₁Z₂ stabilizers
        for i, (q1, q2) in enumerate([(0,1), (1,2)]):
            circuit.h(9)  # Prepare ancilla in |+⟩
            circuit.cz(q1, 9)  # Controlled-Z implements ZZ measurement
            circuit.cz(q2, 9)
            circuit.h(9)  # Transform back to computational basis
            circuit.measure(9, syndrome_reg[i])
            circuit.reset(9)
        
        # Block 2: Z₃Z₄ and Z₄Z₅ stabilizers  
        for i, (q1, q2) in enumerate([(3,4), (4,5)]):
            circuit.h(9)
            circuit.cz(q1, 9)
            circuit.cz(q2, 9)
            circuit.h(9)
            circuit.measure(9, syndrome_reg[i+2])
            circuit.reset(9)
        
        # Block 3: Z₆Z₇ and Z₇Z₈ stabilizers
        for i, (q1, q2) in enumerate([(6,7), (7,8)]):
            circuit.h(9)
            circuit.cz(q1, 9)
            circuit.cz(q2, 9)
            circuit.h(9)
            circuit.measure(9, syndrome_reg[i+4])
            circuit.reset(9)
        
        # Phase-flip stabilizer measurements
        # First decode bit-flip to access phase information
        for block_start in [0, 3, 6]:
            circuit.cx(block_start, block_start+1)
            circuit.cx(block_start, block_start+2)
        
        # Transform to X-basis for phase stabilizer measurement
        for q in [0, 3, 6]:
            circuit.h(q)
        
        # X₀X₁X₂X₃X₄X₅ stabilizer (blocks 1 & 2) 
        for q in [0,1,2,3,4,5]:
            circuit.cx(q, 9)
        circuit.measure(9, syndrome_reg[6])
        circuit.reset(9)

        # X₃X₄X₅X₆X₇X₈ stabilizer (blocks 2 & 3)
        for q in [3,4,5,6,7,8]:
            circuit.cx(q, 9)
        circuit.measure(9, syndrome_reg[7])
        circuit.reset(9)

        return circuit

    def interpret_syndrome_eigenvalues(self, syndrome_bits):
        """
        Interpret syndrome eigenvalues to determine error location and type.
        Returns tuple: (error_type, error_qubit)
        """
        eigenvalues = [1 if bit == 0 else -1 for bit in syndrome_bits]
        
        # Bit-flip error detection (per 3-qubit block)
        for block in range(3):
            s1, s2 = eigenvalues[block*2], eigenvalues[block*2 + 1]
            if s1 == -1 and s2 == 1:    # First qubit in block
                return ('X', block*3)
            elif s1 == -1 and s2 == -1: # Second qubit in block
                return ('X', block*3 + 1)
            elif s1 == 1 and s2 == -1:  # Third qubit in block
                return ('X', block*3 + 2)

        # Phase-flip error detection (per outer code block)
        s_phase1, s_phase2 = eigenvalues[6], eigenvalues[7]
        if s_phase1 == -1 and s_phase2 == 1:   # Phase error in block 1
            return ('Z', 0)  # First qubit of block 1
        elif s_phase1 == -1 and s_phase2 == -1: # Phase error in block 2
            return ('Z', 3)  # First qubit of block 2
        elif s_phase1 == 1 and s_phase2 == -1:  # Phase error in block 3
            return ('Z', 6)  # First qubit of block 3
        
        return ('I', None)  # No error detected


if __name__ == "__main__":
    simulator = AerSimulator() # To run the quantum circuit
    shor = ShorCode()

    # Define error scenarios (0-based indexing)
    errors = [
        ('X', 0), #Applying a bit-flip at 0th qubit 
        ('Z', 1), #Applying a phase-flip at 1st qubit
        ('X', 2), #Applying a bit-flip at 2nd qubit
        ('Z', 3), #Applying a phase-flip at 3rd qubit 
        ('X', 4), #Applying a bit-flip at 4th qubit
        ('Z', 5), #Applying a phase-flip at 5th qubit
        ('X', 6), #Applying a bit-flip at 6th qubit
        ('Z', 7), #Applying a phase-flip at 7th qubit
        ('X', 8)  #Applying a bit-flip at 8th qubit 
    ]

    for error_type, qubit in errors:
        print(f"\n--- Testing error: {error_type} on qubit {qubit} ---")
        
        # Build circuit with 10 qubits (9 data + 1 ancilla) and 8 classical bits (syndrome)
        qr = QuantumRegister(10, 'q')
        cr = ClassicalRegister(8, 'syndrome')
        qc = QuantumCircuit(qr, cr)

        qc.h(0) # Passing a superposition state as initial input
        shor.encode(qc)
        shor.add_error(qc, error_type, qubit)
        shor.syndrome_eigenvalue_measurement(qc)

        # Simulation Part (Quantum Circuit sSimulation)
        transpiled = transpile(qc, simulator)
        result = simulator.run(transpiled).result()
        counts = result.get_counts()

        # Extract the most probable syndrome measurement
        most_likely = max(counts, key=counts.get)
        syndrome_bits = [int(bit) for bit in most_likely[::-1]]  # Qiskit returns bits reversed
        detected_error_type, error_location = shor.interpret_syndrome_eigenvalues(syndrome_bits)

        # Display output
        print(f"Syndrome bits: {syndrome_bits}")
        print(f"Detected error: Type = {detected_error_type}, Qubit = {error_location}")
        # Outputs for Phase flip will be carried to 0th, 3rd and 6th qubit as per theory.
    






