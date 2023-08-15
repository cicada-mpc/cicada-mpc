Feature: Encodings

    Scenario Outline: Encoding Equality
        Given a <lhs>
        And a <rhs>
        Then the encodings should compare <result>

        Examples:
        | lhs                          | rhs                          | result   |
        | default FixedPoint encoding  | Default FixedPoint encoding  | equal    |
        | default FixedPoint encoding  | 16 bit FixedPoint encoding   | equal    |
        | default FixedPoint encoding  | 13 bit FixedPoint encoding   | unequal  |
        | Identity encoding            | Default FixedPoint encoding  | unequal  |
        | Identity encoding            | Identity encoding            | equal    |
        | Bits encoding                | Bits encoding                | equal    |
        | Bits encoding                | Identity encoding            | unequal  |
        | Boolean encoding             | Boolean encoding             | equal    |
        | Boolean encoding             | Identity encoding            | unequal  |


    Scenario Outline: Round Trip Encoding
	Given a <encoding>
	And a <field>
	When <x> is encoded and decoded
    Then the decoded value should be an array or None
	And the decoded value should match <x>

        Examples:
        | encoding                           | field                 | x                     |
        | default FixedPoint encoding        | default Field         | None                  |
        | default FixedPoint encoding        | default Field         | 1                     |
        | default FixedPoint encoding        | default Field         | 2**8                  |
        | default FixedPoint encoding        | default Field         | 2**8+1                |
        | default FixedPoint encoding        | default Field         | 2**8+1.5              |
        | default FixedPoint encoding        | default Field         | 2**16                 |
        | default FixedPoint encoding        | default Field         | 2**16+1               |
        | default FixedPoint encoding        | default Field         | 2**16+1.5             |
        | default FixedPoint encoding        | default Field         | 2**24                 |
        | default FixedPoint encoding        | default Field         | 2**24+1               |
        | default FixedPoint encoding        | default Field         | 2**24+1.5             |
        | default FixedPoint encoding        | default Field         | 2**32                 |
        | default FixedPoint encoding        | default Field         | 2**32+1               |
        | default FixedPoint encoding        | default Field         | 2**32+1.5             |
        | default FixedPoint encoding        | default Field         | 2**46                 |
        | default FixedPoint encoding        | default Field         | 2**46 + 1             |
        | default FixedPoint encoding        | default Field         | 2**46 + 101           |
        | default FixedPoint encoding        | default Field         | 2**46 + 101.5         |
        | default FixedPoint encoding        | default Field         | 2**47 - 1             |
        | default FixedPoint encoding        | default Field         | 2**47 - 2             |
        | default FixedPoint encoding        | default Field         | 2**47 - 2.5           |
        | default FixedPoint encoding        | default Field         | -2**16                |
        | default FixedPoint encoding        | default Field         | -2**24                |
        | default FixedPoint encoding        | default Field         | -2**24 + 1            |
        | default FixedPoint encoding        | default Field         | -2**24 + 1.5          |
        | default FixedPoint encoding        | default Field         | -2**24 - 1            |
        | default FixedPoint encoding        | default Field         | -2**24 - 1.5          |
        | default FixedPoint encoding        | default Field         | -2**24 - 1.25         |
        | default FixedPoint encoding        | default Field         | -2**24 - 1.125        |
        | default FixedPoint encoding        | default Field         | -2**24 - 1.0625       |
        | default FixedPoint encoding        | default Field         | -2**24 - 1.03125      |
        | default FixedPoint encoding        | default Field         | -2**24 - 1.015625     |
        | default FixedPoint encoding        | default Field         | -2**24 - 1.0078125    |
        | default FixedPoint encoding        | default Field         | 35123458              |
        | default FixedPoint encoding        | default Field         | -35123458             |
        | default FixedPoint encoding        | default Field         | 2**25 - 1             |
        | default FixedPoint encoding        | default Field         | -56358025             |
        | default FixedPoint encoding        | default Field         | 56358025              |
        | default FixedPoint encoding        | default Field         | 1.5                   |
        | default FixedPoint encoding        | default Field         | -1.5                  |
        | default FixedPoint encoding        | default Field         | [1.5]                 |
        | default FixedPoint encoding        | default Field         | [1.5,2.5,3.5]         |
        | default FixedPoint encoding        | default Field         | [[1.5,2.5],[3.5,4.5]] |
        | Identity encoding                  | default Field         | None                  |
        | Identity encoding                  | default Field         | 1                     |
        | Identity encoding                  | default Field         | 256                   |
        | Identity encoding                  | default Field         | [1]                   |
        | Identity encoding                  | default Field         | [1, 256]              |
        | Identity encoding                  | default Field         | [[1, 2], [3, 4]]      |
        | Bits encoding                      | default Field         | None                  |
        | Bits encoding                      | default Field         | 0                     |
        | Bits encoding                      | default Field         | 1                     |
        | Bits encoding                      | default Field         | [1]                   |
        | Bits encoding                      | default Field         | [0, 1]                |
        | Boolean encoding                   | default Field         | None                  |
        | Boolean encoding                   | default Field         | 0                     |
        | Boolean encoding                   | default Field         | 1                     |
        | Boolean encoding                   | default Field         | [1]                   |
        | Boolean encoding                   | default Field         | [0, 1]                |

