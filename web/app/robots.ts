import type {MetadataRoute} from "next";import {SITE_URL} from "@/lib/seo-content";
export default function robots():MetadataRoute.Robots{return{rules:[{userAgent:"*",allow:"/",disallow:["/visit","/admin","/design","/louvre-golden20-preview","/api/"]}],sitemap:`${SITE_URL}/sitemap.xml`,host:SITE_URL}}
