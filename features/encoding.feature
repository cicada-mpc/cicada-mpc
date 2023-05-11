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


    Scenario Outline: Round Trip Encoding
	Given a <encoding>
	And a <field>
	When <x> is encoded and decoded
	Then the decoded value should match <x>

        Examples:
        | encoding                           | field                 | x                     |
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
        | default FixedPoint encoding        | default Field         | None                  |

