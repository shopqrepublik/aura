import NextLink from "next/link";
import type {ComponentProps} from "react";
export default function SeoLink(props:ComponentProps<typeof NextLink>){const visitorIntent=typeof props.href==="string"&&props.href.startsWith("/visit");return <NextLink {...props} prefetch={visitorIntent?false:props.prefetch}/>}
