Feature: Encoders

    Scenario Outline: Encoder Equality
        Given a <lhs>
        And a <rhs>
        Then the encoders should compare <result>

        Examples:
        | lhs                       | rhs                                              | result   |
        | 16 bit FixedFieldEncoder  | 16 bit FixedFieldEncoder                         | equal    |
        | 16 bit FixedFieldEncoder  | 13 bit FixedFieldEncoder                         | unequal  |
        | 16 bit FixedFieldEncoder  | 16 bit FixedFieldEncoder mod 123456789           | unequal  |


    Scenario Outline: Encoded Array Shape
        Given a <encoder>
        When <x> is encoded the shape of the encoded array should be <shape>

        Examples:
        | encoder            | x                  | shape             |
        | FixedFieldEncoder  | 1                  | ()                |
        | FixedFieldEncoder  | [1]                | (1,)              |
        | FixedFieldEncoder  | [1,2,3]            | (3,)              |
        | FixedFieldEncoder  | [[1,2,3],[4,5,6]]  | (2, 3)            |


    Scenario Outline: Decoded Array Shape
        Given a <encoder>
        When <x> is encoded the shape of the decoded array should be <shape>

        Examples:
        | encoder            | x                  | shape             |
        | FixedFieldEncoder  | 1                  | ()                |
        | FixedFieldEncoder  | [1]                | (1,)              |
        | FixedFieldEncoder  | [1,2,3]            | (3,)              |
        | FixedFieldEncoder  | [[1,2,3],[4,5,6]]  | (2, 3)            |


    Scenario Outline: Round Trip Encoding
        Given a <encoder>
        When <x> is encoded and decoded the result should match <y>

        Examples:
        | encoder                  | x                  | y                  |
        | 4 bit FixedFieldEncoder  | 1                  | 1                  |
        | FixedFieldEncoder        | 1                  | 1                  |
        | FixedFieldEncoder        | 2**8               | 2**8               |
        | FixedFieldEncoder        | 2**8+1             | 2**8+1             |
        | FixedFieldEncoder        | 2**8+1.5           | 2**8+1.5           |
        | FixedFieldEncoder        | 2**16              | 2**16              |
        | FixedFieldEncoder        | 2**16+1            | 2**16+1            |
        | FixedFieldEncoder        | 2**16+1.5          | 2**16+1.5          |
        | FixedFieldEncoder        | 2**24              | 2**24              |
        | FixedFieldEncoder        | 2**24+1            | 2**24+1            |
        | FixedFieldEncoder        | 2**24+1.5          | 2**24+1.5          |
        | FixedFieldEncoder        | 2**32              | 2**32              |
        | FixedFieldEncoder        | 2**32+1            | 2**32+1            |
        | FixedFieldEncoder        | 2**32+1.5          | 2**32+1.5          |
        | FixedFieldEncoder        | 2**46              | 2**46              |
        | FixedFieldEncoder        | 2**46 + 1          | 2**46 + 1          |
        | FixedFieldEncoder        | 2**46 + 101        | 2**46 + 101        |
        | FixedFieldEncoder        | 2**46 + 101.5      | 2**46 + 101.5      |
        | FixedFieldEncoder        | 2**47 - 1          | 2**47 - 1          |
        | FixedFieldEncoder        | 2**47 - 2          | 2**47 - 2          |
        | FixedFieldEncoder        | 2**47 - 2.5        | 2**47 - 2.5        |
        | FixedFieldEncoder        | -2**16             | -2**16             |
        | FixedFieldEncoder        | -2**24             | -2**24             |
        | FixedFieldEncoder        | -2**24 + 1         | -2**24 + 1         |
        | FixedFieldEncoder        | -2**24 + 1.5       | -2**24 + 1.5       |
        | FixedFieldEncoder        | -2**24 - 1         | -2**24 - 1         |
        | FixedFieldEncoder        | -2**24 - 1.5       | -2**24 - 1.5       |
        | FixedFieldEncoder        | -2**24 - 1.25      | -2**24 - 1.25      |
        | FixedFieldEncoder        | -2**24 - 1.125     | -2**24 - 1.125     |
        | FixedFieldEncoder        | -2**24 - 1.0625    | -2**24 - 1.0625    |
        | FixedFieldEncoder        | -2**24 - 1.03125   | -2**24 - 1.03125   |
        | FixedFieldEncoder        | -2**24 - 1.015625  | -2**24 - 1.015625  |
        | FixedFieldEncoder        | -2**24 - 1.0078125 | -2**24 - 1.0078125 |
        | FixedFieldEncoder        | 35123458           | 35123458           |
        | FixedFieldEncoder        | -35123458          | -35123458          |
        | FixedFieldEncoder        | 2**25 - 1          | 2**25 - 1          |
        | FixedFieldEncoder        | -56358025          | -56358025          |
        | FixedFieldEncoder        | 56358025           | 56358025           |
        | FixedFieldEncoder        | 1.5                | 1.5                |
        | FixedFieldEncoder        | -1.5               | -1.5               |
        | FixedFieldEncoder        | [1.5]              | [1.5]              |
        | FixedFieldEncoder        | [1.5,2.5,3.5]      | [1.5,2.5,3.5]      |
        | FixedFieldEncoder        | [[1.5,2.5],[3.5,4.5]] | [[1.5,2.5],[3.5,4.5]] |


    Scenario: Encoding and Decoding None
        Given a FixedFieldEncoder
        When None is encoded and decoded the result should be None


    Scenario Outline: Zeros
        Given a <encoder>
        When generating zeros with shape <shape> the result should match <result>

        Examples:
        | encoder                  | shape              | result             |
        | FixedFieldEncoder        | ()                 | 0                  |
        | FixedFieldEncoder        | 1                  | [0]                |
        | FixedFieldEncoder        | (2, 3)             | [[0, 0, 0],[0, 0, 0]] |


    Scenario Outline: Zeros Like
        Given a <encoder>
        When generating zeros like <other> the result should match <result>

        Examples:
        | encoder                  | other              | result             |
        | FixedFieldEncoder        | 3                  | 0                  |
        | FixedFieldEncoder        | [3, 4]             | [0, 0]             |
        | FixedFieldEncoder        | [[3,4,5],[5,6,7]]  | [[0, 0, 0],[0, 0, 0]] |


    Scenario Outline: Subtraction
        Given a <encoder>
        When <b> is subtracted from <a> the result should match <c>

        Examples:
        | encoder            | a         | b         | c        |
        | FixedFieldEncoder  | 1         | 1         | 0        |
        | FixedFieldEncoder  | 1         | 3         | -2       |
        | FixedFieldEncoder  | 1.2       | 3.5       | -2.3     |
        | FixedFieldEncoder  | 1.2       | 0         | 1.2      |
        | FixedFieldEncoder  | 0         | 1.2       | -1.2     |


    Scenario Outline: Negation
        Given a <encoder>
        When <a> is negated the result should match <b>

        Examples:
        | encoder            | a         | b         |
        | FixedFieldEncoder  | 0         | 0         |
        | FixedFieldEncoder  | 3         | -3        |
        | FixedFieldEncoder  | 3.5       | -3.5      |
        | FixedFieldEncoder  | -3        | 3         |
        | FixedFieldEncoder  | -3.2      | 3.2       |


    Scenario Outline: Summation
        Given a <encoder>
        When <a> is summed the result should match <b>

        Examples:
        | encoder            | a         | b         |
        | FixedFieldEncoder  | [1, 2, 3] | 6         |


    Scenario Outline: Untruncated Matrix Vector Multiplication
        Given a <encoder>
        When matrix <A> and vector <x> are encoded and multiplied without truncation, the decoded result should match <y>

        Examples:
        | encoder           | A                           | x                           | y                 |
        | FixedFieldEncoder | [[1,2,3],[4,5,6],[0,0,0]]   | [1,1,1]                     | [393216,983040,0] |
        | FixedFieldEncoder | [0, 1, 2, 3, 4, 5, 6, 7, 8] | [0, 1, 2, 3, 4, 5, 6, 7, 8] | 13369344          |


