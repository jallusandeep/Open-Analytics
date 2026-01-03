                                                                                                        # UI Standards & Universal Patterns

This document outlines all universal UI standards and patterns implemented across the Rubik Analytics project.

## Table of Contents
1. [Button Standards](#button-standards)
2. [Icon Standards](#icon-standards)
3. [Toggle/Switch Standards](#toggleswitch-standards)
4. [Search Input Standards](#search-input-standards)
5. [Sidebar Standards](#sidebar-standards)
6. [Animation Standards](#animation-standards)
7. [Accessibility Standards](#accessibility-standards)

---

## Button Standards

### Universal Button Features
- **All buttons must have icons** - Every button should include an appropriate icon from `lucide-react`
- **Hover animations** - Buttons lift slightly (`translateY(-2px)`) and show enhanced shadows on hover
- **Press flash effect** - All buttons have a flash animation on press with ripple effect
- **Standardized classes** - Use `btn-standard` class for consistent behavior

### Button Variants

#### Primary Buttons
- Background: Primary color with gradient on hover
- Shadow: `0 4px 16px rgba(59, 130, 246, 0.4)` on hover
- Transform: `translateY(-2px) scale(1.02)` on hover

#### Secondary Buttons
- Background: Light gray with gradient on hover
- Shadow: `0 4px 12px rgba(0, 0, 0, 0.15)` on hover
- Transform: `translateY(-2px) scale(1.02)` on hover

#### Ghost Buttons
- Background: Transparent with subtle highlight on hover
- Shadow: `0 2px 8px rgba(59, 130, 246, 0.25)` on hover
- Transform: `translateY(-1px) scale(1.01)` on hover

#### Danger Buttons
- Background: Error color with gradient on hover
- Shadow: `0 4px 16px rgba(239, 68, 68, 0.4)` on hover
- Transform: `translateY(-2px) scale(1.02)` on hover

### Button Icon Standards
- **Icon size**: `w-4 h-4` for standard buttons
- **Icon spacing**: `mr-1.5` (margin-right)
- **Icon classes**: Must include `btn-icon-hover` for hover animations
- **Accessibility**: All icons must have `aria-label` attributes

### Common Button Icons
- **Create/Add**: `UserPlus`, `FilePlus`, `Plus`
- **Edit**: `Edit`
- **Delete**: `Trash2`
- **Save**: `Save`
- **Cancel/Close**: `X`, `XIcon`, `XCircle`
- **Search**: `Search`
- **Refresh/Reload**: `RefreshCw`
- **Upload**: `Upload`
- **Download**: `Download`
- **View**: `Eye`
- **Back**: `ArrowLeft`
- **Done/Check**: `Check`
- **Play/Run**: `Play`
- **Remove**: `Minus`

### Example Button Implementation
```tsx
<Button
  variant="primary"
  size="sm"
  onClick={handleAction}
  className="h-9 px-4"
>
  <Search className="w-4 h-4 mr-1.5 btn-icon-hover" aria-label="Search" />
  Search
</Button>
```

---

## Icon Standards

### Icon Button Animations
All icon buttons should have appropriate animations based on their action:

#### Animation Classes
- **`.icon-button`**: Base class for all icon buttons
- **`.icon-button-spin`**: For refresh/reload icons (rotates on hover)
- **`.icon-button-pulse`**: For play/check icons (pulses on hover)
- **`.icon-button-bounce`**: For general action icons (bounces on hover)
- **`.icon-button-shake`**: For delete/close icons (shakes on hover)
- **`.icon-refresh-press`**: For refresh icons (spins on press only, not hover)

### Refresh Icon Special Behavior
- **Refresh icons rotate on press only** - Not on hover, not continuously
- Use class: `icon-refresh-press`
- Animation: 0.6s spin on `:active` state

### Icon Styling
- **Color**: Use explicit hex colors (e.g., `#3b82f6`) instead of Tailwind classes
- **Size**: Standard sizes are `w-4 h-4`, `w-5 h-5`, `w-3 h-3` based on context
- **Accessibility**: All icons must have `aria-label` attributes

### Example Icon Implementation
```tsx
<RefreshCw 
  className="w-4 h-4 mr-1.5 icon-button icon-refresh-press" 
  aria-label="Refresh" 
/>
```

---

## Toggle/Switch Standards

### Universal Switch Component
All toggle buttons must use the standardized `Switch` component from `@/components/ui/Switch`.

### Switch Features
- **Size variants**: `sm`, `md`, `lg`
- **Standardized styling**: Uses `btn-standard` class for hover/press effects
- **Hover effects**: Background darkens on hover
- **Press effects**: Flash animation on click
- **Accessibility**: Proper `role="switch"` and `aria-checked` attributes

### Switch Sizes
- **Small (`sm`)**: `h-4 w-7` - For table rows and compact spaces
- **Medium (`md`)**: `h-6 w-11` - Default size for most use cases
- **Large (`lg`)**: `h-7 w-13` - For prominent settings

### Switch Colors
- **Checked**: Success green (`bg-success`)
- **Unchecked**: Gray (`bg-gray-200 dark:bg-gray-700`)
- **Hover (checked)**: `bg-success/90`
- **Hover (unchecked)**: `bg-gray-300 dark:bg-gray-600`

### Example Switch Implementation
```tsx
<Switch
  checked={isActive}
  onCheckedChange={(checked) => handleToggle(checked)}
  disabled={isDisabled}
  size="sm"
/>
```

### Replaced Custom Toggles
- ✅ Accounts Page: User active/inactive toggles
- ✅ Activity Page: Scheduler active/inactive toggles
- ✅ Settings Page: Theme toggle
- ✅ Connections Page: Connection enabled/disabled toggles
- ✅ UploadSymbolModal: Scheduler active/inactive toggles

---

## Search Input Standards

### Universal Search Pattern
All search inputs must follow the same layout and styling pattern as the symbol search.

### Search Layout Structure
```tsx
<div className="mb-3 flex items-center gap-2">
  <div className="flex-1 max-w-md">
    <Input
      type="text"
      placeholder="Search [items]..."
      value={search}
      onChange={(e) => setSearch(e.target.value)}
      className="h-9"
    />
  </div>
  <Button
    variant="primary"
    size="sm"
    onClick={handleSearch}
    className="h-9 px-4 flex-shrink-0"
    disabled={loading}
  >
    <Search className="w-4 h-4 mr-1.5 btn-icon-hover" aria-label="Search" />
    Search
  </Button>
</div>
```

### Search Input Features
- **Height**: `h-9` for consistent sizing
- **Max width**: `max-w-md` for the input container
- **Search button**: Always includes Search icon and "Search" text
- **Layout**: Flex layout with `gap-2` spacing
- **Button**: Primary variant, small size, with icon

### Standardized Search Pages
- ✅ Symbols Page: Search symbols (reference implementation)
- ✅ Accounts Page: Search users
- ✅ Connections Page: Search connections
- ✅ Reference Data - Indicators: Search indicators
- ✅ Reference Data - Symbols: Search symbols
- ✅ Feature Requests: Search by description or user
- ✅ Feedback: Search feedback

---

## Sidebar Standards

### Sidebar Icon Styling
- **No fill colors**: Icons use `fill: 'none'`
- **Colored borders**: Icons use colored strokes (`stroke: item.color`)
- **Stroke width**: `3` (increased to `3.5` on hover)
- **No glow effects**: Removed all drop-shadow and brightness filters
- **Sharp rendering**: Antialiasing enabled for crisp edges

### Sidebar Icon States
- **Idle**: Clean colored border, no effects
- **Hover**: Slightly thicker stroke (`3.5`), no glow
- **Active**: Colored border, no pulse animation

### Sidebar Positioning
- **Left edge**: Flush with viewport left edge
- **No margins/padding**: `margin: 0, padding: 0` on sidebar element
- **Layout**: Uses flexbox, no absolute positioning

### Sidebar Tooltips
- **Always show on hover**: Tooltips appear on hover for all icons
- **Include descriptions**: Tooltips show icon name and description
- **Smooth animations**: Fade and scale animations

### Example Sidebar Icon
```tsx
<IconComponent 
  className="w-5 h-5 transition-all duration-300" 
  style={{
    color: 'transparent',
    filter: 'none',
    strokeWidth: 3,
    fill: 'none',
    stroke: item.color,
    strokeLinejoin: 'round',
    strokeLinecap: 'round',
    paintOrder: 'stroke'
  }}
/>
```

---

## Animation Standards

### Button Press Flash Animation
All buttons have a flash effect on press:
- **Animation**: `buttonFlash` keyframe (brightness flash)
- **Ripple effect**: Expanding circle on click
- **Duration**: 0.2s-0.3s

### Hover Animations
- **Scale**: Icons scale to `1.1` on hover
- **Lift**: Buttons lift `-2px` on hover
- **Shadows**: Enhanced shadows on hover
- **Transitions**: Smooth `0.2s-0.3s` transitions

### Icon-Specific Animations
- **Spin**: Refresh icons (on press only)
- **Pulse**: Play, check icons
- **Bounce**: General action icons
- **Shake**: Delete, close icons

### Animation Timing
- **Standard transitions**: `duration-200` (200ms)
- **Smooth easing**: `cubic-bezier(0.4, 0, 0.2, 1)`
- **Icon animations**: `0.6s ease-in-out`

---

## Accessibility Standards

### Icon Accessibility
- **All icons must have `aria-label`** attributes
- **Descriptive labels**: Use clear, action-oriented labels
- **Tooltips**: Provide additional context on hover

### Button Accessibility
- **Focus states**: All buttons have visible focus rings
- **Disabled states**: Proper opacity and cursor handling
- **Keyboard navigation**: All interactive elements are keyboard accessible

### Form Accessibility
- **Labels**: All form inputs must have associated labels
- **Error messages**: Clear error feedback
- **Required fields**: Properly marked

### Example Accessible Icon
```tsx
<Edit 
  className="w-4 h-4 icon-button icon-button-bounce" 
  aria-label="Edit user" 
/>
```

---

## CSS Classes Reference

### Button Classes
- `.btn-standard`: Base class for all buttons (hover/press effects)
- `.btn-primary`: Primary button variant
- `.btn-secondary`: Secondary button variant
- `.btn-ghost`: Ghost button variant
- `.btn-danger`: Danger button variant

### Icon Classes
- `.icon-button`: Base icon button class
- `.icon-button-spin`: Spin animation on hover
- `.icon-button-pulse`: Pulse animation on hover
- `.icon-button-bounce`: Bounce animation on hover
- `.icon-button-shake`: Shake animation on hover
- `.icon-refresh-press`: Refresh icon (spins on press only)
- `.btn-icon-hover`: Scale animation on hover

### Animation Keyframes
- `@keyframes buttonFlash`: Button press flash effect
- `@keyframes iconSpin`: Icon rotation animation
- `@keyframes iconPulse`: Icon pulse animation
- `@keyframes iconBounce`: Icon bounce animation
- `@keyframes iconShake`: Icon shake animation

---

## Implementation Checklist

When adding new UI components, ensure:

- [ ] All buttons have icons with proper spacing
- [ ] All buttons use `btn-standard` class
- [ ] All icons have `aria-label` attributes
- [ ] All toggles use the `Switch` component
- [ ] All search inputs follow the standard pattern
- [ ] All icons have appropriate animation classes
- [ ] Hover effects are consistent across components
- [ ] Press effects (flash) are applied
- [ ] Accessibility standards are met
- [ ] Dark mode support is included

---

## Notes

- **Refresh icons**: Only animate on press, not on hover or continuously
- **Sidebar icons**: No fill colors, only colored borders
- **Button icons**: Always include both icon and text label
- **Search inputs**: Always include Search button with icon
- **Toggle buttons**: Always use Switch component, never custom implementations

---

*Last Updated: 2024*
*This document should be updated whenever new universal patterns are established.*

